#!/usr/bin/env python3
"""Fasal Doctor prototype: leaf photo in, simple Hindi/Bhojpuri advice out.

Usage: python3 crop_doctor.py photo.jpg <rice|wheat|potato> [hindi|bhojpuri]
Needs a Gemini API key sent as the x-goog-api-key header (set GEMINI_API_KEY
if running outside Hark).
"""
import base64, json, os, sys, urllib.request

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
FALLBACKS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

PROMPT = """You are a careful plant doctor helping a small farmer in Bihar, India.
The farmer says this photo is of their {crop} crop. Trust that crop name.

Think about every common {crop} disease and pest in North India that could look like this.
Return JSON only, with these keys:
- crop: "{crop}"
- top3: list of 3 objects {{"problem": English name, "likelihood": percent integer}}, most likely first, percents adding to 100
- visible_signs: one short English sentence of what you actually see (colour, shape, pattern of spots or stripes)
- sure: true only if the first guess is at least 70 percent AND the signs are distinctive; otherwise false
- severity: mild | moderate | severe
- reply: a short WhatsApp message in {lang}, Devanagari script, max 90 words, simple village words.
  If sure is true: name the problem, how serious, one common treatment sold in Indian shops
  (generic chemical name and typical label dose), rough cost per acre in rupees.
  If sure is false: name the top 2 possibilities, give NO chemical or dose, and ask for 2 more photos
  (whole plant, and the underside of a leaf, in daylight).
  Always end: "spray se pehle label padhein aur najdiki Krishi Vigyan Kendra (KVK) se salah lein" (in {lang}).
"""

def diagnose(path, crop, lang="hindi"):
    img = base64.b64encode(open(path, "rb").read()).decode()
    body = {
        "contents": [{"parts": [
            {"text": PROMPT.format(crop=crop, lang="Bhojpuri" if lang == "bhojpuri" else "Hindi")},
            {"inline_data": {"mime_type": "image/jpeg", "data": img}},
        ]}],
        "generationConfig": {"response_mime_type": "application/json", "temperature": 0.2},
    }
    headers = {"Content-Type": "application/json"}
    if os.environ.get("GEMINI_API_KEY"):
        headers["x-goog-api-key"] = os.environ["GEMINI_API_KEY"]
    import time, urllib.error
    models = [MODEL] + [m for m in FALLBACKS if m != MODEL]
    last = None
    for attempt in range(4):
        for m in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
            try:
                out = json.load(urllib.request.urlopen(req, timeout=90))
                break
            except (urllib.error.HTTPError, TimeoutError) as e:
                last = e; out = None
        if out: break
        time.sleep(10 * (attempt + 1))
    if not out:
        raise RuntimeError(f"Gemini busy, try again later: {last}")
    txt = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"] if not p.get("thought"))
    return json.loads(txt)

if __name__ == "__main__":
    print(json.dumps(diagnose(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "hindi"),
                     ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""Fasal Doctor v3: decides it is "sure" only when 3 independent runs agree.

Usage: python3 crop_doctor_v3.py photo.jpg <rice|wheat|potato> [hindi|bhojpuri]

How it works
1. Diagnose 3 times in parallel (temperature 1.0), each run must pick from a fixed
   list of disease codes for that crop, so the answers can be compared exactly.
2. Verdict: 3/3 agree -> "sure"; 2/3 -> "likely"; otherwise -> "unsure".
3. Advice comes from TREATMENTS below (a fixed table), never from the model.
   Doses are NOT in the table: farmers are told to follow the label. The table
   still needs a KVK / CIB&RC review before real use.
4. One last call writes the WhatsApp reply in Hindi/Bhojpuri using only those facts.
"""
import base64, json, os, sys, time, urllib.request, urllib.error
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]

DISEASES = {
    "rice": ["blast", "brown_spot", "bacterial_leaf_blight", "bacterial_leaf_streak", "sheath_blight",
             "narrow_brown_spot", "false_smut", "tungro", "zinc_deficiency", "stem_borer", "leaf_folder",
             "brown_planthopper", "healthy", "other"],
    "wheat": ["yellow_rust", "brown_rust", "black_rust", "powdery_mildew", "spot_blotch", "tan_spot",
              "septoria_blotch", "loose_smut", "karnal_bunt", "aphid", "nutrient_deficiency", "healthy", "other"],
    "potato": ["late_blight", "early_blight", "leafroll_virus", "mosaic_virus_pvy", "black_scurf", "common_scab",
               "bacterial_wilt", "frost_damage", "nutrient_deficiency", "healthy", "other"],
}

# Generic actions only, no doses. Needs KVK review before real use.
TREATMENTS = {
    "blast": "Tricyclazole fungicide spray (label dose); avoid extra urea.",
    "brown_spot": "Mancozeb fungicide spray (label dose); give balanced fertiliser, especially potash.",
    "bacterial_leaf_blight": "No fungicide cures it. Drain standing water for a few days, stop extra urea; ask KVK about copper-based spray.",
    "bacterial_leaf_streak": "No fungicide cures it. Stop extra urea, keep field drained; ask KVK.",
    "sheath_blight": "Hexaconazole or Validamycin spray at the base of plants (label dose); avoid dense planting and extra urea.",
    "narrow_brown_spot": "Usually mild. Balanced fertiliser; spray only if spreading, ask KVK.",
    "false_smut": "Propiconazole spray at booting stage (label dose) prevents it next time; remove smut balls.",
    "tungro": "Virus, no spray cures it. Pull out sick plants, control green leafhopper; ask KVK.",
    "zinc_deficiency": "Not a disease: Zinc sulphate (label dose) to soil or as spray.",
    "stem_borer": "Insect: ask KVK for the right insecticide; light traps help.",
    "leaf_folder": "Insect: ask KVK for the right insecticide.",
    "brown_planthopper": "Insect: drain field, avoid extra urea; ask KVK for insecticide.",
    "yellow_rust": "Propiconazole or Tebuconazole spray (label dose) quickly, before it spreads.",
    "brown_rust": "Propiconazole or Tebuconazole spray (label dose).",
    "black_rust": "Propiconazole or Tebuconazole spray (label dose); inform KVK.",
    "powdery_mildew": "Propiconazole or wettable sulphur spray (label dose).",
    "spot_blotch": "Propiconazole spray (label dose); balanced fertiliser.",
    "tan_spot": "Propiconazole spray (label dose) if spreading.",
    "septoria_blotch": "Propiconazole spray (label dose) if spreading.",
    "loose_smut": "No spray helps now. Next season treat seed (Carboxin or Tebuconazole seed dressing).",
    "karnal_bunt": "No spray helps now. Use clean seed next season; inform KVK.",
    "aphid": "Insect: spray only if many aphids; ask KVK for insecticide.",
    "late_blight": "Mancozeb spray to protect; if spreading fast, Cymoxanil+Mancozeb (label dose). Spreads quickly in cold damp weather.",
    "early_blight": "Mancozeb spray (label dose); remove badly affected lower leaves.",
    "leafroll_virus": "Virus, no spray cures it. Pull out sick plants, control aphids, use certified seed next time.",
    "mosaic_virus_pvy": "Virus, no spray cures it. Pull out sick plants, control aphids, use certified seed next time.",
    "black_scurf": "Seed-tuber problem: treat seed before planting next time; ask KVK.",
    "common_scab": "Soil problem: keep soil moist during tuber growth; treat seed next time.",
    "bacterial_wilt": "No spray cures it. Remove wilted plants with soil; rotate crop; ask KVK.",
    "frost_damage": "Not a disease: light irrigation on frost nights helps.",
    "nutrient_deficiency": "Likely fertiliser shortage: get soil tested at KVK.",
    "healthy": "No spray needed. Keep checking every few days.",
    "other": "Not clear from photo; show to KVK.",
}

DIAG_PROMPT = """You are a plant doctor in Bihar, India. The farmer says this photo is their {crop} crop.
Choose the single most likely problem from this exact list of codes:
{codes}
Return JSON only: {{"code": one code from the list, "signs": one short sentence of what you see}}"""

REPLY_PROMPT = """Write a short WhatsApp message in {lang} (Devanagari, simple village words, max 80 words)
to a Bihar farmer about their {crop} crop. Use ONLY these facts, add no chemical, dose or price of your own:
Verdict: {verdict}
Problem: {problem}
{alt}
What to do: {action}
Rules: if verdict is "likely", say it is probably {problem} but not certain, give the action, and ask for one more
close photo in daylight. If verdict is "unsure", name the possibilities, give NO chemical, ask for 2 more photos
(whole plant and close-up of leaf, in daylight). Always end by saying: read the label before spraying and
consult the nearest Krishi Vigyan Kendra (KVK). Return plain text only."""


def _call(parts, temperature, json_out=True):
    body = {"contents": [{"parts": parts}], "generationConfig": {"temperature": temperature}}
    if json_out:
        body["generationConfig"]["response_mime_type"] = "application/json"
    headers = {"Content-Type": "application/json"}
    if os.environ.get("GEMINI_API_KEY"):
        headers["x-goog-api-key"] = os.environ["GEMINI_API_KEY"]
    last = None
    for attempt in range(4):
        for m in MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers)
            try:
                out = json.load(urllib.request.urlopen(req, timeout=90))
                txt = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"] if not p.get("thought"))
                return json.loads(txt) if json_out else txt.strip()
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
                last = e
        time.sleep(8 * (attempt + 1))
    raise RuntimeError(f"Gemini busy: {last}")


def diagnose(path, crop, lang="hindi", runs=3):
    img = {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(open(path, "rb").read()).decode()}}
    codes = DISEASES[crop]
    prompt = {"text": DIAG_PROMPT.format(crop=crop, codes=", ".join(codes))}
    with ThreadPoolExecutor(runs) as ex:
        results = list(ex.map(lambda _: _call([prompt, img], 1.0), range(runs)))
    votes = [r.get("code") if r.get("code") in codes else "other" for r in results]
    top, n = Counter(votes).most_common(1)[0]
    verdict = "sure" if n == runs else "likely" if n * 2 > runs else "unsure"
    if top == "other" and verdict == "sure":
        verdict = "unsure"
    others = [c for c in dict.fromkeys(votes) if c != top]
    alt = f"Other possibility: {', '.join(c.replace('_', ' ') for c in others)}" if others else ""
    action = TREATMENTS[top] if verdict != "unsure" else "Do not spray yet; send more photos or show to KVK."
    reply = _call([{"text": REPLY_PROMPT.format(lang="Bhojpuri" if lang == "bhojpuri" else "Hindi", crop=crop,
                    verdict=verdict, problem=top.replace("_", " "), alt=alt, action=action)}], 0.3, json_out=False)
    return {"crop": crop, "votes": votes, "verdict": verdict, "problem": top, "action": action,
            "signs": results[0].get("signs"), "reply": reply}


if __name__ == "__main__":
    print(json.dumps(diagnose(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "hindi"),
                     ensure_ascii=False, indent=2))

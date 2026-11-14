# Hark prototypes

- `crop-doctor/` — Fasal Doctor: a Hindi crop-disease helper for wheat, rice and potato. It uses Gemini, with 3 parallel votes that must pick from a fixed disease list, and a fixed treatment table. Prototype only; the treatments still need review by a KVK.
- `loan-reset-alert/` — Loan Reset Alert: a page for Indian floating-rate borrowers, with a rates table, an EMI-change calculator and a repricing letter.

The API key is read from the `GEMINI_API_KEY` environment variable and is never committed.

# local-ui-ops-mvp

Local-only MVP to prove **vision-first UI control** on your own computer (no containers).  
Focus: **pixel-true `<canvas>`**, normalized coordinates, and **DPI-safe clicks** via Selenium element offsets.

## What this repo gives you
- **Exact scaling math**: element-only screenshots, PNG size, CSS rects, and image↔CSS scale factors.
- **Normalized [0..1] contract**: models return normalized coords, we convert **once** back to element offsets.
- **Selenium driver**: open pages, capture element PNG, click via element offsets (DPI-safe).
- **Pluggable vision**: `src/vision/providers.py` stubs for ChatGPT‑5 Vision or Zhipu **GLM‑4.5V** (OpenAI‑compatible). You’ll wire the HTTP calls using the included prompt.
- **Big bootstrap prompt**: `prompts/full_bootstrap_prompt.txt` tells an agent exactly how to finish wiring providers and run end-to-end tests.

> If a provider returns non‑normalized formats (pixel or 0–1000), we **normalize to [0..1]** using the actual screenshot size—no ambiguity.

---

## Quick start

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
# put your keys in .env

# Smoke test (no vision needed): open example.com and click near center of the body
python -m src.drivers.browser_selenium
```

### Browser demo (with or without a vision provider)
```bash
# Center click only (no provider)
python -m src.demos.browser_demo --pages "https://example.com,https://news.ycombinator.com" --selector "body" --center-only

# Try provider (after wiring providers.py as per the prompt; set VISION_PROVIDER=openai or zai in .env)
python -m src.demos.browser_demo --pages "https://example.com,https://news.ycombinator.com" --selector "body"
```

---

## How scaling works (short)
1) We screenshot the **element only** and measure its PNG `(png_w,png_h)` and CSS rect `(css_w,css_h)`.  
2) We ask your VLM to return **normalized [0..1]** coords **relative to the image it sees**.  
3) We convert normalized→PNG pixels→**CSS element offsets**, then click via Selenium.  
   - This avoids OS DPI/multi-monitor issues.

See: `src/vision/normalizer.py` and `src/drivers/browser_selenium.py`.

---

## Files to know
- `src/vision/normalizer.py` — One-shot normalization, scale derivation, and element offset math, with debug helpers.
- `src/drivers/browser_selenium.py` — Minimal Selenium wrapper + a built‑in smoke test.
- `src/vision/providers.py` — Stubs for OpenAI (GPT‑5 Vision) and Zhipu (GLM‑4.5V). Fill in with the included prompt.
- `src/demos/browser_demo.py` — Opens pages, screenshots target element, and either center‑clicks or calls your provider to click the returned point.

---

## Troubleshooting
- **Clicks offset or miss?** Check the debug line printed by `browser_demo` (shows PNG/CSS sizes, scales, offsets).
- **Windows DPI scaling:** The method uses **element offsets** so DPI should not matter. If it does, ensure browser window isn’t maximized under weird per‑monitor DPI mixes.
- **Multiple monitors:** Prefer keeping the browser on your main monitor initially.

---

## License
MIT for this scaffold. Your model/API licenses apply for providers.

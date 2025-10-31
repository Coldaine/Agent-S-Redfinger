from __future__ import annotations
import base64, os, json, time
from typing import Optional, Dict, Any, List, Tuple
import requests

from .normalizer import extract_json_object

"""
Vision providers that call OpenAI-compatible vision chat completions.

API:
    analyze_image(image_bytes: bytes, provider: str, model: str) -> str
Returns: provider text (expected to contain STRICT JSON with normalized coords).

Contract and behavior:
- Always include the system prompt verbatim below and the user prompt.
- Send the element PNG as-is as a base64 data URL (no resizing).
- After receiving model text, attempt to parse JSON. If it fails, retry once with a terse system nudge.
- If parsed coords appear outside [0,1], we'll note that in logs; clamping happens downstream.
- Return the raw provider text either way so the caller can show and parse it.
"""

SYSTEM_PROMPT = (
    "You are a vision-to-action tool. Given a single image, return ONLY this JSON with normalized coordinates in [0,1] relative to the image you received:\n"
    "{\n"
    "  \"version\":\"1.0\",\n"
    "  \"coords\":{\"space\":\"normalized\",\"x\": <float 0..1>,\"y\": <float 0..1>},\n"
    "  \"why\":\"<short>\",\n"
    "  \"confidence\": <0.0..1.0>\n"
    "}\n"
    "Rules:\n"
    "- One JSON object. No extra text, no code fences.\n"
    "- (0,0)=top-left, (1,1)=bottom-right.\n"
    "- If uncertain, still output your best guess with confidence<=0.3."
)

USER_PROMPT_EXAMPLE = (
    "Here is an image of a mobile game screen. Identify the single best place to click to start the daily mission. Return STRICT JSON per the schema."
)

def b64_png(image_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")

def _build_messages(user_prompt: str, image_data_url: str) -> List[Dict[str, Any]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": image_data_url}},
            ],
        },
    ]

def _post_chat_completions(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, Any]],
    timeout: float = 30.0,
) -> Tuple[str, Dict[str, Any]]:
    """POST to an OpenAI-compatible chat/completions endpoint and return (text, raw_response_json)."""
    url = base_url.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        # Keep responses deterministic-ish to reduce prose risk
        "temperature": 0.2,
    }
    # GPT-5 models use max_completion_tokens, older models use max_tokens
    if model.startswith("gpt-5") or model.startswith("o3") or model.startswith("o4"):
        payload["max_completion_tokens"] = 300
    else:
        payload["max_tokens"] = 300
    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Provider HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    try:
        text = data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"Malformed provider response: {e}; body={str(data)[:300]}")
    return text, data

def analyze_image(image_bytes: bytes, provider: str, model: str) -> str:
    provider = (provider or "none").lower()
    # Disallow expensive "pro" variants per project policy
    if model and isinstance(model, str) and "pro" in model.lower():
        raise RuntimeError("Model variants with '-pro' are disabled by policy. Use gpt-5 or gpt-5-mini (or nano).")
    if provider == "none":
        # Return a center prediction in strict JSON for smoke tests.
        return json.dumps({"version":"1.0","coords":{"space":"normalized","x":0.5,"y":0.5},"why":"center","confidence":0.1})

    # Build base64 image data URL once (element-only screenshot, no resizing)
    img_url = b64_png(image_bytes)
    user_prompt = USER_PROMPT_EXAMPLE
    messages = _build_messages(user_prompt, img_url)

    # Provider routing
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
    elif provider == "zai":
        api_key = os.getenv("ZAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("ZAI_API_KEY not set")
        base_url = os.getenv("ZAI_BASE_URL", "https://api.bigmodel.org")
    else:
        raise NotImplementedError(f"Provider '{provider}' not implemented yet")

    # First attempt
    text, raw = _post_chat_completions(base_url, api_key, model, messages)
    print(f"Provider({provider}) raw: {text[:120].replace('\n',' ')}")

    # Try to extract JSON; if fails, retry once with a terse nudge
    need_retry = False
    try:
        parsed = extract_json_object(text)
        _log_if_out_of_range(parsed)
    except Exception:
        need_retry = True

    if need_retry:
        nudged = [{"role": "system", "content": "Return JSON only, no extra text."}] + messages
        # Sanitize image payload for log
        sanitized = json.dumps({
            "model": model,
            "messages": [
                {**m, **({"content": "(omitted image + text)"} if isinstance(m.get("content"), list) else {})}
                for m in nudged
            ],
        })
        print(f"Retry payload (sanitized): {sanitized[:200]}...")
        text2, _raw2 = _post_chat_completions(base_url, api_key, model, nudged)
        print(f"Provider({provider}) raw: {text2[:120].replace('\n',' ')}")
        # Try to parse second response for logging/clamp note only; always return raw text
        try:
            parsed2 = extract_json_object(text2)
            _log_if_out_of_range(parsed2)
        except Exception:
            pass
        text = text2

    # Success indicator (printed per call)
    print(f"{('OpenAI' if provider=='openai' else 'zai') } provider wired ✔")
    return text

def _log_if_out_of_range(parsed: Dict[str, Any]) -> None:
    try:
        coords = parsed.get("coords") if isinstance(parsed, dict) else None
        if not isinstance(coords, dict):
            return
        x = coords.get("x"); y = coords.get("y")
        if x is None or y is None:
            return
        fx = float(x); fy = float(y)
        out = []
        if fx < 0.0 or fx > 1.0:
            out.append("x")
        if fy < 0.0 or fy > 1.0:
            out.append("y")
        if out:
            print(f"note: provider coords out of [0,1] for {','.join(out)} — will clamp downstream")
    except Exception:
        # Be quiet on logging errors; downstream will still handle clamping/normalization
        pass

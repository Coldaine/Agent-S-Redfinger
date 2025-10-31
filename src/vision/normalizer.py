from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal, Tuple, Optional, Any, Dict

CoordSpace = Literal["normalized", "pixel", "0-1000", "grid1000"]


@dataclass(frozen=True)
class Frame:
    w: int
    h: int
    space: CoordSpace  # the space x,y are expressed in for this frame (usually "pixel")


@dataclass
class NormResult:
    nx: float
    ny: float
    src_space: CoordSpace
    src_w: Optional[int]
    src_h: Optional[int]
    note: str = ""


def clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)


def to_normalized(
    x: float,
    y: float,
    src_space: CoordSpace,
    src_w: Optional[int] = None,
    src_h: Optional[int] = None,
) -> NormResult:
    if src_space == "normalized":
        return NormResult(
            clamp01(float(x)), clamp01(float(y)), "normalized", None, None, "pass-through"
        )
    if src_space in ("0-1000", "grid1000"):
        nx = clamp01(float(x) / 1000.0)
        ny = clamp01(float(y) / 1000.0)
        return NormResult(nx, ny, src_space, None, None, "grid1000→normalized")
    if src_space == "pixel":
        if not src_w or not src_h or src_w <= 0 or src_h <= 0:
            raise ValueError("to_normalized(pixel): src_w/src_h required and must be > 0")
        nx = clamp01(float(x) / float(src_w))
        ny = clamp01(float(y) / float(src_h))
        return NormResult(nx, ny, "pixel", src_w, src_h, "pixel→normalized")
    raise ValueError(f"Unknown src_space={src_space}")


def derive_image_to_css_scales(
    png_w: int, png_h: int, css_w: float, css_h: float
) -> Tuple[float, float]:
    if css_w <= 0 or css_h <= 0:
        raise ValueError("CSS width/height must be > 0")
    sx = float(png_w) / float(css_w)
    sy = float(png_h) / float(css_h)
    return sx, sy


@dataclass
class Offsets:
    off_x: int
    off_y: int
    nx: float
    ny: float
    png_w: int
    png_h: int
    css_w: float
    css_h: float
    scale_x: float
    scale_y: float


def normalized_to_element_offsets(
    nx: float,
    ny: float,
    png_w: int,
    png_h: int,
    css_w: float,
    css_h: float,
) -> Offsets:
    nx = clamp01(nx)
    ny = clamp01(ny)
    scale_x, scale_y = derive_image_to_css_scales(png_w, png_h, css_w, css_h)
    px_img = nx * png_w
    py_img = ny * png_h
    off_x = int(round(px_img / scale_x))
    off_y = int(round(py_img / scale_y))
    off_x = max(0, min(off_x, int(css_w) - 1))
    off_y = max(0, min(off_y, int(css_h) - 1))
    return Offsets(
        off_x, off_y, nx, ny, png_w, png_h, css_w, css_h, scale_x, scale_y
    )


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_by_brace_match(text: str) -> Optional[str]:
    in_str = False
    esc = False
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if esc:
            esc = False
            continue
        if ch == "\\":
            esc = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{" and depth == 0:
            start = i
            depth = 1
            continue
        if ch == "{" and depth > 0:
            depth += 1
            continue
        if ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start != -1:
                return text[start:i + 1]
    return None


def extract_json_object(text: str) -> Dict[str, Any]:
    text = text.strip()
    # Fast path
    if text.startswith("{"):
        return json.loads(text)  # type: ignore[no-any-return]
    # Try robust brace-matching first
    candidate = _extract_by_brace_match(text)
    if candidate:
        return json.loads(candidate)  # type: ignore[no-any-return]
    # Fall back to greedy regex as a last resort
    m = _JSON_OBJECT_RE.search(text)
    if m:
        return json.loads(m.group(0))  # type: ignore[no-any-return]
    raise ValueError("No JSON object found in provider response.")


def coerce_provider_coords(
    provider_json: Dict[str, Any],
    fallback_space: CoordSpace,
    src_w: Optional[int],
    src_h: Optional[int],
) -> NormResult:
    coords = provider_json.get("coords")
    if isinstance(coords, dict):
        space = coords.get("space", fallback_space)
        x = coords.get("x")
        y = coords.get("y")
    else:
        space = provider_json.get("space", fallback_space)
        x = provider_json.get("x")
        y = provider_json.get("y")
    if x is None or y is None:
        raise ValueError("Provider JSON missing x/y")
    return to_normalized(x, y, src_space=space, src_w=src_w, src_h=src_h)


def explain_offsets(offsets: Offsets) -> str:
    return (
        f"normalized=({offsets.nx:.4f},{offsets.ny:.4f})  "
        f"png=({offsets.png_w}x{offsets.png_h})  css=({offsets.css_w}x{offsets.css_h})  "
        f"scale=({offsets.scale_x:.3f},{offsets.scale_y:.3f})  "
        f"offset=({offsets.off_x},{offsets.off_y})"
    )

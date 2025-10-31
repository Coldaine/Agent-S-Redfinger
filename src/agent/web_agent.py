from __future__ import annotations

import io
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import re

from PIL import Image

from src.drivers.browser_selenium import SeleniumCanvasDriver
from src.vision.normalizer import Frame
from src.vision import providers
from selenium.webdriver.common.by import By


@dataclass
class AgentConfig:
    provider: str = "none"  # "openai", "zai", or "none" for center-only model
    model: str = "gpt-5-vision"
    selector: str = "body"
    max_steps: int = 3
    step_delay_s: float = 1.2
    center_fallback: bool = True
    stop_on_navigation: bool = True


class VisionWebAgent:
    """
    Minimal agent that iterates: observe -> propose click (vision) -> act.

    The vision provider is prompted to return normalized coords only; the agent executes
    a click within the element defined by selector. This is intentionally tiny and safe.
    """

    def __init__(self, drv: Optional[SeleniumCanvasDriver] = None) -> None:
        self.drv = drv or SeleniumCanvasDriver()

    def run(self, start_url: str, goal: str, cfg: Optional[AgentConfig] = None) -> Dict[str, Any]:
        cfg = cfg or AgentConfig()
        log: Dict[str, Any] = {"steps": []}
        self.drv.open(start_url)
        try:
            for step in range(cfg.max_steps):
                # Observe
                png = self.drv.element_png(cfg.selector)
                with Image.open(io.BytesIO(png)) as im:
                    pw, ph = im.size

                # Decide
                user_prompt = (
                    "Goal: "
                    + goal
                    + "\nReturn STRICT JSON with normalized x,y for the single best click to progress."
                )
                vision_error = None
                raw_text = None
                try:
                    raw_text = providers.analyze_image(
                        png, cfg.provider, cfg.model, user_prompt=user_prompt
                    )
                except Exception as e:
                    vision_error = str(e)

                # Execute
                prev_url = None
                if getattr(self.drv, "driver", None):
                    try:
                        prev_url = self.drv.driver.current_url  # type: ignore[assignment]
                    except Exception:
                        prev_url = None
                if raw_text is not None:
                    frame = Frame(w=pw, h=ph, space="pixel")  # allow pixel coords from providers
                    info = self.drv.click_from_provider_json(
                        cfg.selector, raw_text, fallback_space="normalized", src_frame=frame
                    )
                else:
                    info = self._dom_keyword_click(cfg.selector, goal)
                # Give the page time to respond or navigate
                time.sleep(cfg.step_delay_s)
                post_url = None
                if getattr(self.drv, "driver", None):
                    try:
                        post_url = self.drv.driver.current_url  # type: ignore[assignment]
                    except Exception:
                        post_url = None
                navigated = bool(prev_url and post_url and prev_url != post_url)

                entry = {
                    "step": step + 1,
                    "click": info,
                    "prev_url": prev_url,
                    "post_url": post_url,
                    "navigated": navigated,
                }
                if vision_error:
                    entry["vision_error"] = vision_error
                log["steps"].append(entry)

                if cfg.stop_on_navigation and navigated:
                    log["status"] = "navigated"
                    break

            log["status"] = "ok"
            return log
        finally:
            self.drv.close()

    def _dom_keyword_click(self, selector: str, goal: str) -> Dict[str, Any]:
        """Fallback: click an anchor within the selector using simple keyword matching.

        Intended only for smoke-testing when the vision provider isn't available.
        """
        if not getattr(self.drv, "driver", None):
            raise RuntimeError("Driver not open")
        root = self.drv._find(selector)
        anchors = root.find_elements(By.TAG_NAME, "a")
        tokens = [t for t in _tokenize(goal) if len(t) >= 3]
        best = None
        best_score = -1
        for a in anchors:
            try:
                txt = (a.text or "").strip().lower()
                href = (a.get_attribute("href") or "").strip()
            except Exception:
                continue
            score = sum(1 for t in tokens if t in txt)
            if score > best_score:
                best_score = score
                best = (a, txt, href)
        if not best and anchors:
            a = anchors[0]
            txt = (a.text or "").strip().lower()
            href = (a.get_attribute("href") or "").strip()
            best = (a, txt, href)
        if not best:
            raise RuntimeError("No anchors found for DOM fallback")
        a, txt, href = best
        a.click()
        return {"strategy": "dom-fallback", "anchor_text": txt, "href": href}


def _tokenize(s: str) -> List[str]:
    return [w for w in re.split(r"[^a-z0-9]+", s.lower()) if w]

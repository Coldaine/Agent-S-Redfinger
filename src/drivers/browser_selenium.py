from __future__ import annotations
import io
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

from src.vision.normalizer import (
    Frame, to_normalized, normalized_to_element_offsets,
    coerce_provider_coords, extract_json_object, explain_offsets, CoordSpace
)

@dataclass
class ElementRect:
    x: float
    y: float
    width: float
    height: float

class SeleniumCanvasDriver:
    def __init__(self, browser: str = "chrome"):
        self.browser = browser.lower()
        self.driver: Optional[webdriver.Chrome] = None

    # Custom exception to make error handling explicit at call sites
    class DriverNotOpenError(RuntimeError):
        pass

    def open(self, start_url: Optional[str] = None):
        if self.browser != "chrome":
            raise NotImplementedError("Only Chrome is wired by default; extend as needed.")
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--force-device-scale-factor=1")
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1280, 900)
        if start_url:
            self.driver.get(start_url)
            time.sleep(0.8)

    def close(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    def goto(self, url: str):
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        self.driver.get(url)
        time.sleep(0.5)

    def _find(self, selector: str):
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        return self.driver.find_element(By.CSS_SELECTOR, selector)

    def element_rect(self, selector: str) -> ElementRect:
        el = self._find(selector)
        r = el.rect
        return ElementRect(x=r["x"], y=r["y"], width=r["width"], height=r["height"])

    def element_png(self, selector: str) -> bytes:
        el = self._find(selector)
        return el.screenshot_as_png

    @staticmethod
    def png_size(png_bytes: bytes) -> Tuple[int, int]:
        with Image.open(io.BytesIO(png_bytes)) as im:
            return im.size  # (w, h)

    def click_normalized(self, selector: str, nx: float, ny: float, png_w: int, png_h: int) -> Dict:
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        # For type-checkers
        assert self.driver is not None
        el = self._find(selector)
        rect = el.rect  # css pixels
        off = normalized_to_element_offsets(
            nx, ny,
            png_w=png_w, png_h=png_h,
            css_w=rect["width"], css_h=rect["height"]
        )
        # Selenium's move_to_element_with_offset uses offsets from element CENTER, not top-left
        # So we need to adjust: offset_from_center = offset_from_topleft - (width/2, height/2)
        center_off_x = off.off_x - int(rect["width"] / 2)
        center_off_y = off.off_y - int(rect["height"] / 2)
        ActionChains(self.driver).move_to_element_with_offset(el, center_off_x, center_off_y).click().perform()
        return {
            "selector": selector,
            "rect": rect,
            "offset_x": off.off_x,
            "offset_y": off.off_y,
            "explain": explain_offsets(off),
        }

    def click_from_provider_json(
        self,
        selector: str,
        provider_text: str,
        fallback_space: CoordSpace,
        src_frame: Optional[Frame],
    ) -> Dict:
        data = extract_json_object(provider_text)
        if src_frame and src_frame.space == "pixel":
            norm = coerce_provider_coords(data, fallback_space=fallback_space,
                                          src_w=src_frame.w, src_h=src_frame.h)
        else:
            norm = coerce_provider_coords(data, fallback_space=fallback_space,
                                          src_w=None, src_h=None)
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        # For type-checkers
        assert self.driver is not None
        el = self._find(selector)
        rect = el.rect
        png_bytes = el.screenshot_as_png
        png_w, png_h = self.png_size(png_bytes)
        off = normalized_to_element_offsets(norm.nx, norm.ny, png_w, png_h, rect["width"], rect["height"])
        # Selenium's move_to_element_with_offset uses offsets from element CENTER, not top-left
        center_off_x = off.off_x - int(rect["width"] / 2)
        center_off_y = off.off_y - int(rect["height"] / 2)
        ActionChains(self.driver).move_to_element_with_offset(el, center_off_x, center_off_y).click().perform()
        return {
            "selector": selector,
            "rect": rect,
            "offset_x": off.off_x,
            "offset_y": off.off_y,
            "normalized": (norm.nx, norm.ny),
            "explain": explain_offsets(off),
        }

if __name__ == "__main__":
    drv = SeleniumCanvasDriver()
    try:
        drv.open("https://example.com")
        selector = "body"
        png = drv.element_png(selector)
        pw, ph = drv.png_size(png)
        info = drv.click_normalized(selector, 0.5, 0.5, png_w=pw, png_h=ph)
        print("Clicked:", info["explain"])
        time.sleep(0.5)
    finally:
        drv.close()

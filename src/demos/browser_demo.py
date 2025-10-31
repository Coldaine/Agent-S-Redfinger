from __future__ import annotations

import io
import os
import time
from typing import List
from dotenv import load_dotenv
from PIL import Image

from src.drivers.browser_selenium import SeleniumCanvasDriver
from src.vision.normalizer import extract_json_object, Frame
from src.vision import providers


def run(pages: List[str], selector: str, center_only: bool = False) -> None:
    load_dotenv()
    provider = os.getenv("VISION_PROVIDER", "none")
    model = os.getenv("VISION_MODEL", "gpt-5-vision")

    drv = SeleniumCanvasDriver()
    try:
        drv.open(pages[0] if pages else None)
        if pages:
            time.sleep(0.8)
        for url in pages:
            print(f"\n==> {url}")
            drv.goto(url)
            png = drv.element_png(selector)
            with Image.open(io.BytesIO(png)) as im:
                pw, ph = im.size
            if center_only or provider == "none":
                nx, ny = 0.5, 0.5
                print(f"[center-only] nx,ny=({nx},{ny})  png=({pw}x{ph})")
                info = drv.click_normalized(selector, nx, ny, pw, ph)
                print("CLICK:", info["explain"])
                continue

            # Provider path
            raw_text = providers.analyze_image(png, provider, model)
            data = extract_json_object(raw_text)
            # Allow providers to send pixel coords; if so supply the image frame
            space = (data.get("coords") or data).get("space", "normalized")
            frame = Frame(w=pw, h=ph, space="pixel") if space == "pixel" else None
            # The selenium click helper re-screenshots to compute CSS offsets safely
            info = drv.click_from_provider_json(
                selector, raw_text, fallback_space="normalized", src_frame=frame
            )
            print("CLICK:", info["explain"])

    finally:
        drv.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Browser UI automation demo with vision providers"
    )
    parser.add_argument(
        "--pages",
        type=str,
        default="https://example.com,https://news.ycombinator.com",
        help="Comma-separated list of URLs to visit",
    )
    parser.add_argument(
        "--selector", type=str, default="body", help="CSS selector for the element to interact with"
    )
    parser.add_argument(
        "--center-only",
        action="store_true",
        help="Use center-only clicks without calling vision provider",
    )
    args = parser.parse_args()

    pages = [p.strip() for p in args.pages.split(",") if p.strip()]
    run(pages, selector=args.selector, center_only=args.center_only)

from __future__ import annotations

import io
import time
from dataclasses import dataclass
import os
from typing import Optional, Tuple, Dict, Any

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

from src.vision.normalizer import (
    Frame,
    normalized_to_element_offsets,
    coerce_provider_coords,
    extract_json_object,
    explain_offsets,
    CoordSpace,
)


@dataclass
class ElementRect:
    x: float
    y: float
    width: float
    height: float


class SeleniumCanvasDriver:
    def __init__(self, browser: str = "chrome", profile_dir: Optional[str] = None):
        self.browser = browser.lower()
        self.driver: Optional[webdriver.Chrome] = None
        # Default to environment variable if not explicitly provided
        self.profile_dir = profile_dir or os.getenv("CHROME_PROFILE_DIR")
        self._keep_alive = False
        self._human_control_detected = False
        self._last_human_activity = None

    # Custom exception to make error handling explicit at call sites
    class DriverNotOpenError(RuntimeError):
        pass

    def open(self, start_url: Optional[str] = None) -> None:
        if self.browser != "chrome":
            raise NotImplementedError("Only Chrome is wired by default; extend as needed.")
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--force-device-scale-factor=1")
        
        # If we plan to keep the browser open for human use after automation,
        # tell ChromeDriver to detach so Chrome stays open even if the driver exits.
        # This can be toggled either via set_keep_alive(True) before open(), or
        # via an env var AGENT_KEEP_BROWSER_OPEN=1/true/yes.
        keep_env = (os.getenv("AGENT_KEEP_BROWSER_OPEN", "").lower() in {"1", "true", "yes"})
        if self._keep_alive or keep_env:
            try:
                options.add_experimental_option("detach", True)
                # Disable automation banner for a cleaner handover UI
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option("useAutomationExtension", False)
            except Exception as e:
                print(f"Warning: Could not set Chrome detach option: {e}")
        
        # Add Chrome profile support (robust handling of user-data-dir and profile-directory)
        if self.profile_dir:
            eff = self.profile_dir.rstrip("\\/")
            base = os.path.basename(eff)
            parent = os.path.dirname(eff)
            print(f"🔐 Using Chrome profile: {self.profile_dir}")
            try:
                # If a known profile subdirectory was provided (e.g., Default, Profile 1, AgentProfile)
                if base.lower() in {"default", "profile 1", "profile 2", "profile 3", "agentprofile"}:
                    # Point user-data-dir at the parent folder and select specific profile
                    options.add_argument(f"--user-data-dir={parent}")
                    options.add_argument(f"--profile-directory={base}")
                else:
                    # Treat provided path as the user data root
                    options.add_argument(f"--user-data-dir={eff}")
            except Exception as e:
                print(f"Warning: Could not apply Chrome profile options: {e}")
        
        from selenium.webdriver.chrome.service import Service

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_window_size(1280, 900)
        if start_url:
            self.driver.get(start_url)
            time.sleep(0.8)

    def close(self) -> None:
        if self.driver:
            if self._keep_alive or (os.getenv("AGENT_KEEP_BROWSER_OPEN", "").lower() in {"1", "true", "yes"}):
                # Leave the browser open for human control; just drop our handle
                print("🛑 Not closing Chrome (keep-open enabled). Browser remains available for you.")
                try:
                    self.remove_human_activity_monitors()
                except Exception:
                    pass
                self.driver = None
                return
            self.driver.quit()
            self.driver = None

    def goto(self, url: str) -> None:
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        self.driver.get(url)
        time.sleep(0.5)

    def _find(self, selector: str) -> Any:
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        return self.driver.find_element(By.CSS_SELECTOR, selector)

    def element_rect(self, selector: str) -> ElementRect:
        el = self._find(selector)
        r = el.rect
        return ElementRect(x=r["x"], y=r["y"], width=r["width"], height=r["height"])

    def element_png(self, selector: str) -> bytes:
        el = self._find(selector)
        return el.screenshot_as_png  # type: ignore[no-any-return]

    @staticmethod
    def png_size(png_bytes: bytes) -> Tuple[int, int]:
        with Image.open(io.BytesIO(png_bytes)) as im:
            return im.size  # type: ignore[no-any-return] (w, h)

    def click_normalized(
        self, selector: str, nx: float, ny: float, png_w: int, png_h: int
    ) -> Dict[str, Any]:
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        # For type-checkers
        assert self.driver is not None
        el = self._find(selector)
        rect = el.rect  # css pixels
        off = normalized_to_element_offsets(
            nx, ny, png_w=png_w, png_h=png_h, css_w=rect["width"], css_h=rect["height"]
        )
        # Selenium's move_to_element_with_offset uses offsets from element CENTER, not top-left
        # So we need to adjust: offset_from_center = offset_from_topleft - (width/2, height/2)
        center_off_x = off.off_x - int(rect["width"] / 2)
        center_off_y = off.off_y - int(rect["height"] / 2)
        ActionChains(self.driver).move_to_element_with_offset(
            el, center_off_x, center_off_y
        ).click().perform()
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
    ) -> Dict[str, Any]:
        data = extract_json_object(provider_text)
        if src_frame and src_frame.space == "pixel":
            norm = coerce_provider_coords(
                data, fallback_space=fallback_space, src_w=src_frame.w, src_h=src_frame.h
            )
        else:
            norm = coerce_provider_coords(
                data, fallback_space=fallback_space, src_w=None, src_h=None
            )
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        # For type-checkers
        assert self.driver is not None
        el = self._find(selector)
        rect = el.rect
        png_bytes = el.screenshot_as_png
        png_w, png_h = self.png_size(png_bytes)
        off = normalized_to_element_offsets(
            norm.nx, norm.ny, png_w, png_h, rect["width"], rect["height"]
        )
        # Selenium's move_to_element_with_offset uses offsets from element CENTER, not top-left
        center_off_x = off.off_x - int(rect["width"] / 2)
        center_off_y = off.off_y - int(rect["height"] / 2)
        ActionChains(self.driver).move_to_element_with_offset(
            el, center_off_x, center_off_y
        ).click().perform()
        return {
            "selector": selector,
            "rect": rect,
            "offset_x": off.off_x,
            "offset_y": off.off_y,
            "normalized": (norm.nx, norm.ny),
            "explain": explain_offsets(off),
        }

    # New methods for session handover support
    def set_keep_alive(self, keep_alive: bool = True) -> None:
        """
        Set whether to keep browser alive after script completion.
        
        Args:
            keep_alive: If True, browser will remain open after operations
        """
        self._keep_alive = keep_alive
    
    def is_kept_alive(self) -> bool:
        """
        Check if browser is set to be kept alive.
        
        Returns:
            bool: True if browser should be kept alive
        """
        return self._keep_alive
    
    def detect_human_control(self) -> bool:
        """
        Detect if browser is currently under human control.
        
        This method checks for signs of human interaction:
        - Recent mouse movements
        - Keyboard activity
        - Page navigation by user
        - Changes in browser focus
        
        Returns:
            bool: True if human control is detected
        """
        if not self.driver:
            return False
        
        try:
            # Check for recent user activity through JavaScript
            # This is a simple heuristic - more sophisticated detection could be added
            
            # Check if page has focus (indicating user interaction)
            has_focus = self.driver.execute_script("return document.hasFocus();")
            if has_focus:
                self._human_control_detected = True
                return True
            
            # Check for recent mouse movements
            last_mouse_move = self.driver.execute_script("""
                return window.lastMouseMoveTime || 0;
            """)
            
            if last_mouse_move:
                import time
                current_time = time.time() * 1000  # JavaScript timestamp in milliseconds
                time_diff = current_time - last_mouse_move
                
                # If mouse moved within last 5 seconds, consider it human control
                if time_diff < 5000:
                    self._human_control_detected = True
                    return True
            
            # Check for recent keyboard activity
            last_keypress = self.driver.execute_script("""
                return window.lastKeypressTime || 0;
            """)
            
            if last_keypress:
                import time
                current_time = time.time() * 1000
                time_diff = current_time - last_keypress
                
                # If key pressed within last 5 seconds, consider it human control
                if time_diff < 5000:
                    self._human_control_detected = True
                    return True
            
            return self._human_control_detected
            
        except Exception as e:
            print(f"Warning: Could not detect human control: {e}")
            return False
    
    def install_human_activity_monitors(self) -> None:
        """
        Install JavaScript monitors to detect human activity.
        
        This method adds event listeners to track:
        - Mouse movements
        - Keyboard presses
        - Page focus changes
        """
        if not self.driver:
            return
        
        try:
            # JavaScript to monitor human activity
            activity_monitor_script = """
            // Track mouse movements
            document.addEventListener('mousemove', function() {
                window.lastMouseMoveTime = Date.now();
            });
            
            // Track keyboard activity
            document.addEventListener('keydown', function() {
                window.lastKeypressTime = Date.now();
            });
            
            // Track page focus
            window.addEventListener('focus', function() {
                window.pageFocusTime = Date.now();
            });
            
            // Initialize tracking variables
            window.lastMouseMoveTime = 0;
            window.lastKeypressTime = 0;
            window.pageFocusTime = 0;
            
            return true;
            """
            
            self.driver.execute_script(activity_monitor_script)
            print("✅ Human activity monitors installed")
            
        except Exception as e:
            print(f"Warning: Could not install activity monitors: {e}")
    
    def remove_human_activity_monitors(self) -> None:
        """
        Remove JavaScript monitors for human activity detection.
        """
        if not self.driver:
            return
        
        try:
            # JavaScript to remove activity monitors
            cleanup_script = """
            // Remove event listeners (this is a simplified cleanup)
            delete window.lastMouseMoveTime;
            delete window.lastKeypressTime;
            delete window.pageFocusTime;
            
            return true;
            """
            
            self.driver.execute_script(cleanup_script)
            print("🧹 Human activity monitors removed")
            
        except Exception as e:
            print(f"Warning: Could not remove activity monitors: {e}")
    
    def keep_browser_alive(self, message: Optional[str] = None) -> None:
        """
        Keep browser alive and display a message to the user.
        
        Args:
            message: Optional message to display to the user
        """
        if not self.driver:
            print("Warning: No browser instance to keep alive")
            return
        
        self._keep_alive = True
        
        if message:
            print(f"\n{'='*80}")
            print(f"🤖 BROWSER SESSION PERSISTENCE")
            print(f"{'='*80}")
            print(message)
            print(f"{'='*80}\n")
        
        # Install activity monitors
        self.install_human_activity_monitors()
        
        print("🔄 Browser will remain open for human interaction")
        print("💡 The browser is now under your control")
        print("🖱️  You can interact with the page normally")
        print("⏹️  Close the browser manually when done, or call close() to terminate")
    
    def force_close(self) -> None:
        """
        Force close the browser regardless of keep_alive setting.
        """
        print("🔄 Force closing browser...")
        self.remove_human_activity_monitors()
        self.close()
    
    def get_browser_status(self) -> Dict[str, Any]:
        """
        Get current browser status information.
        
        Returns:
            Dict[str, Any]: Browser status information
        """
        status = {
            "driver_open": self.driver is not None,
            "keep_alive": self._keep_alive,
            "human_control_detected": self._human_control_detected,
            "current_url": None,
            "title": None,
            "window_handles": 0
        }
        
        if self.driver:
            try:
                status["current_url"] = self.driver.current_url
                status["title"] = self.driver.title
                status["window_handles"] = len(self.driver.window_handles)
            except Exception as e:
                status["error"] = str(e)
        
        return status
    
    def refresh_page(self) -> None:
        """
        Refresh the current page.
        """
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        
        self.driver.refresh()
        time.sleep(0.5)  # Wait for page to reload
    
    def execute_javascript(self, script: str, *args) -> Any:
        """
        Execute JavaScript in the browser.
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script
            
        Returns:
            Any: Result of the JavaScript execution
        """
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        
        return self.driver.execute_script(script, *args)
    
    def get_page_source(self) -> str:
        """
        Get the current page source.
        
        Returns:
            str: HTML source of the current page
        """
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        
        return self.driver.page_source
    
    def take_screenshot(self, filename: Optional[str] = None) -> bytes:
        """
        Take a screenshot of the current page.
        
        Args:
            filename: Optional filename to save the screenshot
            
        Returns:
            bytes: Screenshot as PNG bytes
        """
        if not self.driver:
            raise SeleniumCanvasDriver.DriverNotOpenError("Driver not open. Call open() first.")
        
        screenshot = self.driver.get_screenshot_as_png()
        
        if filename:
            try:
                with open(filename, "wb") as f:
                    f.write(screenshot)
                print(f"📸 Screenshot saved: {filename}")
            except Exception as e:
                print(f"Warning: Could not save screenshot to {filename}: {e}")
        
        return screenshot


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

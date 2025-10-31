from __future__ import annotations

import io
import time
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
import re

from PIL import Image

from src.drivers.browser_selenium import SeleniumCanvasDriver
from src.vision.normalizer import Frame
from src.vision import providers
from selenium.webdriver.common.by import By
from src.agent.session_manager import SessionManager, SessionConfig


@dataclass
class AgentConfig:
    provider: str = "none"  # "openai", "zai", or "none" for center-only model
    model: str = os.getenv("VISION_MODEL", "gpt-5-mini")
    selector: str = "body"
    max_steps: int = 3
    step_delay_s: float = 1.2
    center_fallback: bool = True
    stop_on_navigation: bool = True
    log_dir: Optional[str] = None  # Directory to save screenshots and logs
    profile_dir: Optional[str] = None  # Chrome profile directory path


class VisionWebAgent:
    """
    Minimal agent that iterates: observe -> propose click (vision) -> act.

    The vision provider is prompted to return normalized coords only; the agent executes
    a click within the element defined by selector. This is intentionally tiny and safe.
    """

    def __init__(self, drv: Optional[SeleniumCanvasDriver] = None, profile_dir: Optional[str] = None) -> None:
        # Prefer explicit argument, otherwise fall back to env var CHROME_PROFILE_DIR
        eff_profile = profile_dir or os.getenv("CHROME_PROFILE_DIR")
        self.drv = drv or SeleniumCanvasDriver(profile_dir=eff_profile)
        self.profile_dir = eff_profile
        self.session_manager: Optional[SessionManager] = None

    def run(self, start_url: str, goal: str, cfg: Optional[AgentConfig] = None) -> Dict[str, Any]:
        cfg = cfg or AgentConfig()
        log: Dict[str, Any] = {"start_url": start_url, "goal": goal, "steps": []}
        
        # Use profile from config if not set in constructor
        if cfg.profile_dir and not self.profile_dir:
            self.drv = SeleniumCanvasDriver(profile_dir=cfg.profile_dir)
        
        # Allow keeping the browser open after automation via env toggle
        # or a future cfg flag (not yet in AgentConfig to avoid breaking changes).
        if os.getenv("AGENT_KEEP_BROWSER_OPEN", "").lower() in {"1", "true", "yes"}:
            self.drv.set_keep_alive(True)
        
        # Setup logging directory
        log_dir = None
        if cfg.log_dir:
            log_dir = Path(cfg.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n{'='*80}")
            print(f"🔍 AGENT RUN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            print(f"📍 START URL: {start_url}")
            print(f"🎯 GOAL: {goal}")
            print(f"📂 LOGS: {log_dir.absolute()}")
            if cfg.profile_dir:
                print(f"🔐 CHROME PROFILE: {cfg.profile_dir}")
            print(f"{'='*80}\n")
        # Open or reuse an existing browser session
        created_driver_here = False
        if getattr(self.drv, "driver", None):
            if start_url:
                try:
                    self.drv.goto(start_url)
                except Exception:
                    # If reuse fails, fall back to reopen
                    self.drv.close()
                    self.drv.open(start_url)
                    created_driver_here = True
        else:
            self.drv.open(start_url)
            created_driver_here = True
        
        # Log initial page state
        if log_dir:
            initial_screenshot = self.drv.driver.get_screenshot_as_png() if self.drv.driver else None
            if initial_screenshot:
                screenshot_path = log_dir / "step_0_initial_page.png"
                with open(screenshot_path, "wb") as f:
                    f.write(initial_screenshot)
                print(f"📸 Saved initial page screenshot: {screenshot_path.name}")
                print(f"   Current URL: {self.drv.driver.current_url if self.drv.driver else 'N/A'}\n")
        
        try:
            for step in range(cfg.max_steps):
                step_num = step + 1
                if log_dir:
                    print(f"\n{'─'*80}")
                    print(f"⚡ STEP {step_num}/{cfg.max_steps}")
                    print(f"{'─'*80}")
                
                # Observe
                png = self.drv.element_png(cfg.selector)
                with Image.open(io.BytesIO(png)) as im:
                    pw, ph = im.size
                
                # Save element screenshot
                screenshot_path = None
                if log_dir:
                    screenshot_path = log_dir / f"step_{step_num}_element.png"
                    with open(screenshot_path, "wb") as f:
                        f.write(png)
                    print(f"📸 Captured element screenshot: {screenshot_path.name}")
                    print(f"   Element: selector='{cfg.selector}', size={pw}x{ph}px")

                # Decide
                user_prompt = (
                    "Goal: "
                    + goal
                    + "\nReturn STRICT JSON with normalized x,y for the single best click to progress."
                )
                vision_error = None
                raw_text = None
                
                if log_dir:
                    print(f"\n🤖 Calling vision provider: {cfg.provider} / {cfg.model}")
                
                try:
                    raw_text = providers.analyze_image(
                        png, cfg.provider, cfg.model, user_prompt=user_prompt
                    )
                    if log_dir and raw_text:
                        print(f"✅ Vision response received: {raw_text[:150]}...")
                except Exception as e:
                    vision_error = str(e)
                    if log_dir:
                        print(f"❌ Vision error: {vision_error}")

                # Execute
                prev_url = None
                if getattr(self.drv, "driver", None):
                    try:
                        prev_url = self.drv.driver.current_url  # type: ignore[assignment]
                    except Exception:
                        prev_url = None
                
                if log_dir:
                    print(f"\n🖱️  Executing click...")
                
                if raw_text is not None:
                    frame = Frame(w=pw, h=ph, space="pixel")  # allow pixel coords from providers
                    info = self.drv.click_from_provider_json(
                        cfg.selector, raw_text, fallback_space="normalized", src_frame=frame
                    )
                    if log_dir:
                        print(f"   Strategy: vision-guided")
                        print(f"   Click info: {info.get('explain', info)}")
                else:
                    info = self._dom_keyword_click(cfg.selector, goal)
                    if log_dir:
                        print(f"   Strategy: DOM fallback")
                        print(f"   Clicked: {info}")
                
                # Give the page time to respond or navigate
                time.sleep(cfg.step_delay_s)
                
                post_url = None
                if getattr(self.drv, "driver", None):
                    try:
                        post_url = self.drv.driver.current_url  # type: ignore[assignment]
                    except Exception:
                        post_url = None
                navigated = bool(prev_url and post_url and prev_url != post_url)
                
                # Save post-action screenshot
                if log_dir and self.drv.driver:
                    post_screenshot = self.drv.driver.get_screenshot_as_png()
                    post_path = log_dir / f"step_{step_num}_after_click.png"
                    with open(post_path, "wb") as f:
                        f.write(post_screenshot)
                    print(f"\n📸 Saved post-click screenshot: {post_path.name}")
                    print(f"   Navigation: {'✅ YES' if navigated else '⛔ NO'}")
                    if navigated:
                        print(f"   From: {prev_url}")
                        print(f"   To:   {post_url}")
                    else:
                        print(f"   URL:  {post_url}")

                entry = {
                    "step": step_num,
                    "click": info,
                    "prev_url": prev_url,
                    "post_url": post_url,
                    "navigated": navigated,
                    "screenshot": str(screenshot_path.name) if screenshot_path else None,
                }
                if vision_error:
                    entry["vision_error"] = vision_error
                log["steps"].append(entry)

                if cfg.stop_on_navigation and navigated:
                    log["status"] = "navigated"
                    if log_dir:
                        print(f"\n✅ Navigation detected - stopping (stop_on_navigation=True)")
                    break

            log["status"] = log.get("status", "ok")
            
            if log_dir:
                print(f"\n{'='*80}")
                print(f"✅ AGENT RUN COMPLETE")
                print(f"   Status: {log['status']}")
                print(f"   Steps: {len(log['steps'])}")
                print(f"{'='*80}\n")
            
            return log
        finally:
            # Only close the driver if we created it in this call
            # This prevents detaching mid-run when a higher-level orchestrator
            # is managing a single session across multiple run() calls.
            if created_driver_here:
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
    def pause_for_human_takeover(self, session_config: Optional[SessionConfig] = None) -> None:
        """
        Pause automation and prepare browser for human takeover.
        
        This method:
        1. Initializes the session manager if not already done
        2. Captures current browser state
        3. Starts handover mode with visual indicators
        4. Keeps browser open for human interaction
        
        Args:
            session_config: Optional session configuration. Uses defaults if not provided.
        """
        if not self.drv.driver:
            raise RuntimeError("Browser driver not open. Call run() first or open browser manually.")
        
        # Initialize session manager if not already done
        if self.session_manager is None:
            self.session_manager = SessionManager(self.drv, session_config)
        
        # Start handover mode
        self.session_manager.start_handover_mode()
    
    def resume_from_human_takeover(self) -> bool:
        """
        Resume automation after human takeover period.
        
        This method:
        1. Ends handover mode
        2. Restores browser state
        3. Removes visual indicators
        4. Returns control to automation
        
        Returns:
            bool: True if successfully resumed, False otherwise
        """
        if self.session_manager is None:
            print("Warning: No active session manager found. Browser may not be in handover mode.")
            return False
        
        return self.session_manager.end_handover_mode()
    
    def is_under_human_control(self) -> bool:
        """
        Check if browser is currently under human control.
        
        Returns:
            bool: True if browser is in handover mode, False otherwise
        """
        if self.session_manager is None:
            return False
        
        return self.session_manager.is_under_human_control()
    
    def get_session_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current session information.
        
        Returns:
            Optional[Dict[str, Any]]: Session information or None if no session manager
        """
        if self.session_manager is None:
            return None
        
        return self.session_manager.get_session_info()
    
    def cleanup_session(self) -> None:
        """
        Clean up session and close browser gracefully.
        
        This method:
        1. Ends any active handover mode
        2. Captures final state
        3. Closes browser session
        4. Cleans up temporary files
        """
        if self.session_manager:
            self.session_manager.cleanup_session()
        elif self.drv.driver:
            # Fallback: just close the browser if no session manager
            print("🤖 Closing browser session...")
            self.drv.close()
    
    def run_with_handover(self, start_url: str, goal: str, cfg: Optional[AgentConfig] = None, 
                         session_config: Optional[SessionConfig] = None, 
                         handover_after_steps: Optional[int] = None) -> Dict[str, Any]:
        """
        Run automation with optional human takeover capability.
        
        This enhanced version of run() adds session handover functionality:
        1. Runs automation for specified steps or full completion
        2. Optionally pauses for human takeover at specified step
        3. Can resume automation after human interaction
        4. Maintains browser session throughout the process
        
        Args:
            start_url: Starting URL for automation
            goal: Goal description for the automation
            cfg: Agent configuration
            session_config: Session management configuration
            handover_after_steps: Step number after which to pause for human takeover
                                 (None for no handover, or 'all' to handover after completion)
        
        Returns:
            Dict[str, Any]: Execution log with handover information
        """
        cfg = cfg or AgentConfig()
        log: Dict[str, Any] = {"start_url": start_url, "goal": goal, "steps": [], "handover_info": {}}
        
        # Use profile from config if not set in constructor
        if cfg.profile_dir and not self.profile_dir:
            self.drv = SeleniumCanvasDriver(profile_dir=cfg.profile_dir)
        
        # Setup logging directory
        log_dir = None
        if cfg.log_dir:
            log_dir = Path(cfg.log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            print(f"\n{'='*80}")
            print(f"🔍 AGENT RUN WITH HANDOVER: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            print(f"📍 START URL: {start_url}")
            print(f"🎯 GOAL: {goal}")
            print(f"📂 LOGS: {log_dir.absolute()}")
            if cfg.profile_dir:
                print(f"🔐 CHROME PROFILE: {cfg.profile_dir}")
            if handover_after_steps:
                if handover_after_steps == 'all':
                    print(f"🤝 HANDOVER: After completion")
                else:
                    print(f"🤝 HANDOVER: After step {handover_after_steps}")
            print(f"{'='*80}\n")
        
        # If we will handover at any point (including after completion), ensure keep-alive is set
        if handover_after_steps is not None:
            self.drv.set_keep_alive(True)
        self.drv.open(start_url)
        
        # Initialize session manager
        self.session_manager = SessionManager(self.drv, session_config)
        
        # Log initial page state
        if log_dir:
            initial_screenshot = self.drv.driver.get_screenshot_as_png() if self.drv.driver else None
            if initial_screenshot:
                screenshot_path = log_dir / "step_0_initial_page.png"
                with open(screenshot_path, "wb") as f:
                    f.write(initial_screenshot)
                print(f"📸 Saved initial page screenshot: {screenshot_path.name}")
                print(f"   Current URL: {self.drv.driver.current_url if self.drv.driver else 'N/A'}\n")
        
        try:
            for step in range(cfg.max_steps):
                step_num = step + 1
                if log_dir:
                    print(f"\n{'─'*80}")
                    print(f"⚡ STEP {step_num}/{cfg.max_steps}")
                    print(f"{'─'*80}")
                
                # Check if we should handover after this step
                should_handover = (handover_after_steps == step_num or 
                                 (handover_after_steps == 'all' and step_num == cfg.max_steps))
                
                # Observe
                png = self.drv.element_png(cfg.selector)
                with Image.open(io.BytesIO(png)) as im:
                    pw, ph = im.size
                
                # Save element screenshot
                screenshot_path = None
                if log_dir:
                    screenshot_path = log_dir / f"step_{step_num}_element.png"
                    with open(screenshot_path, "wb") as f:
                        f.write(png)
                    print(f"📸 Captured element screenshot: {screenshot_path.name}")
                    print(f"   Element: selector='{cfg.selector}', size={pw}x{ph}px")

                # Decide
                user_prompt = (
                    "Goal: "
                    + goal
                    + "\nReturn STRICT JSON with normalized x,y for the single best click to progress."
                )
                vision_error = None
                raw_text = None
                
                if log_dir:
                    print(f"\n🤖 Calling vision provider: {cfg.provider} / {cfg.model}")
                
                try:
                    raw_text = providers.analyze_image(
                        png, cfg.provider, cfg.model, user_prompt=user_prompt
                    )
                    if log_dir and raw_text:
                        print(f"✅ Vision response received: {raw_text[:150]}...")
                except Exception as e:
                    vision_error = str(e)
                    if log_dir:
                        print(f"❌ Vision error: {vision_error}")

                # Execute
                prev_url = None
                if getattr(self.drv, "driver", None):
                    try:
                        prev_url = self.drv.driver.current_url  # type: ignore[assignment]
                    except Exception:
                        prev_url = None
                
                if log_dir:
                    print(f"\n🖱️  Executing click...")
                
                if raw_text is not None:
                    frame = Frame(w=pw, h=ph, space="pixel")  # allow pixel coords from providers
                    info = self.drv.click_from_provider_json(
                        cfg.selector, raw_text, fallback_space="normalized", src_frame=frame
                    )
                    if log_dir:
                        print(f"   Strategy: vision-guided")
                        print(f"   Click info: {info.get('explain', info)}")
                else:
                    info = self._dom_keyword_click(cfg.selector, goal)
                    if log_dir:
                        print(f"   Strategy: DOM fallback")
                        print(f"   Clicked: {info}")
                
                # Give the page time to respond or navigate
                time.sleep(cfg.step_delay_s)
                
                post_url = None
                if getattr(self.drv, "driver", None):
                    try:
                        post_url = self.drv.driver.current_url  # type: ignore[assignment]
                    except Exception:
                        post_url = None
                navigated = bool(prev_url and post_url and prev_url != post_url)
                
                # Save post-action screenshot
                if log_dir and self.drv.driver:
                    post_screenshot = self.drv.driver.get_screenshot_as_png()
                    post_path = log_dir / f"step_{step_num}_after_click.png"
                    with open(post_path, "wb") as f:
                        f.write(post_screenshot)
                    print(f"\n📸 Saved post-click screenshot: {post_path.name}")
                    print(f"   Navigation: {'✅ YES' if navigated else '⛔ NO'}")
                    if navigated:
                        print(f"   From: {prev_url}")
                        print(f"   To:   {post_url}")
                    else:
                        print(f"   URL:  {post_url}")

                entry = {
                    "step": step_num,
                    "click": info,
                    "prev_url": prev_url,
                    "post_url": post_url,
                    "navigated": navigated,
                    "screenshot": str(screenshot_path.name) if screenshot_path else None,
                }
                if vision_error:
                    entry["vision_error"] = vision_error
                log["steps"].append(entry)

                if cfg.stop_on_navigation and navigated:
                    log["status"] = "navigated"
                    if log_dir:
                        print(f"\n✅ Navigation detected - stopping (stop_on_navigation=True)")
                    break
                
                # Handle handover if requested
                if should_handover:
                    log["handover_info"]["handover_step"] = step_num
                    log["handover_info"]["handover_time"] = datetime.now().isoformat()
                    
                    if log_dir:
                        print(f"\n🤝 Initiating handover after step {step_num}")
                    
                    # Start handover mode
                    self.pause_for_human_takeover(session_config)
                    
                    log["status"] = "handover_initiated"
                    if log_dir:
                        print(f"\n{'='*80}")
                        print(f"🤝 HANDOVER INITIATED")
                        print(f"   Step: {step_num}")
                        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"   Browser ready for human takeover")
                        print(f"   Use resume_from_human_takeover() to continue automation")
                        print(f"{'='*80}\n")
                    
                    return log

            log["status"] = log.get("status", "ok")
            
            # Handle handover after completion if requested
            if handover_after_steps == 'all':
                log["handover_info"]["handover_step"] = "completion"
                log["handover_info"]["handover_time"] = datetime.now().isoformat()
                
                if log_dir:
                    print(f"\n🤝 Automation completed. Initiating handover...")
                
                # Start handover mode
                self.pause_for_human_takeover(session_config)
                
                log["status"] = "completed_with_handover"
                if log_dir:
                    print(f"\n{'='*80}")
                    print(f"🤝 HANDOVER AFTER COMPLETION")
                    print(f"   Steps completed: {len(log['steps'])}")
                    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"   Browser ready for human takeover")
                    print(f"   Use resume_from_human_takeover() to continue automation")
                    print(f"{'='*80}\n")
            
            if log_dir:
                print(f"\n{'='*80}")
                print(f"✅ AGENT RUN COMPLETE")
                print(f"   Status: {log['status']}")
                print(f"   Steps: {len(log['steps'])}")
                print(f"{'='*80}\n")
            
            return log
        except Exception as e:
            log["status"] = "error"
            log["error"] = str(e)
            if log_dir:
                print(f"\n❌ AGENT RUN ERROR: {e}")
            raise
        finally:
            # Only close browser if not in handover mode
            if not self.is_under_human_control():
                self.drv.close()


def _tokenize(s: str) -> List[str]:
    return [w for w in re.split(r"[^a-z0-9]+", s.lower()) if w]

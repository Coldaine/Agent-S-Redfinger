from __future__ import annotations

import json
import time
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import os

from src.drivers.browser_selenium import SeleniumCanvasDriver


@dataclass
class SessionState:
    """Represents the current state of a browser session"""
    session_id: str
    start_time: datetime
    last_activity: datetime
    is_handover_active: bool = False
    handover_start_time: Optional[datetime] = None
    handover_timeout: Optional[datetime] = None
    browser_title: str = ""
    current_url: str = ""
    cookies: list = None
    local_storage: Dict[str, str] = None
    session_storage: Dict[str, str] = None
    
    def __post_init__(self):
        if self.cookies is None:
            self.cookies = []
        if self.local_storage is None:
            self.local_storage = {}
        if self.session_storage is None:
            self.session_storage = {}


@dataclass
class SessionConfig:
    """Configuration for session management"""
    keep_open: bool = True
    handover_timeout_minutes: int = 30
    heartbeat_interval_seconds: int = 5
    state_save_interval_seconds: int = 10
    visual_indicators: bool = True
    handover_message: str = "🤖 Automation paused. Browser ready for human takeover."
    resume_message: str = "🤖 Automation resumed. Taking control of browser session."
    cleanup_message: str = "🤖 Automation complete. Browser session will be closed."


class SessionManager:
    """
    Manages browser session persistence during human takeover periods.
    
    Handles:
    - Browser session persistence during human takeover
    - State serialization/deserialization for session recovery
    - Timeout management for human takeover periods
    - Clean handoff notifications to the user
    """
    
    def __init__(self, driver: SeleniumCanvasDriver, config: Optional[SessionConfig] = None):
        self.driver = driver
        self.config = config or SessionConfig()
        self.state = SessionState(
            session_id=f"session_{int(time.time())}",
            start_time=datetime.now(),
            last_activity=datetime.now()
        )
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._state_lock = threading.Lock()
        self._callbacks: Dict[str, Callable] = {}
        
        # State persistence
        self.state_file = Path(f"session_state_{self.state.session_id}.json")
        
    def register_callback(self, event: str, callback: Callable) -> None:
        """Register a callback for session events"""
        self._callbacks[event] = callback
        
    def _trigger_callback(self, event: str, **kwargs) -> None:
        """Trigger registered callbacks"""
        if event in self._callbacks:
            try:
                self._callbacks[event](**kwargs)
            except Exception as e:
                print(f"Warning: Callback for {event} failed: {e}")
    
    def capture_session_state(self) -> SessionState:
        """Capture current browser session state"""
        if not self.driver.driver:
            return self.state
            
        try:
            # Update basic state
            self.state.current_url = self.driver.driver.current_url
            self.state.browser_title = self.driver.driver.title
            self.state.last_activity = datetime.now()
            
            # Capture cookies
            try:
                self.state.cookies = self.driver.driver.get_cookies()
            except Exception as e:
                print(f"Warning: Could not capture cookies: {e}")
                self.state.cookies = []
            
            # Capture localStorage
            try:
                local_storage_script = """
                var items = {};
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    items[key] = localStorage.getItem(key);
                }
                return items;
                """
                self.state.local_storage = self.driver.driver.execute_script(local_storage_script)
            except Exception as e:
                print(f"Warning: Could not capture localStorage: {e}")
                self.state.local_storage = {}
            
            # Capture sessionStorage
            try:
                session_storage_script = """
                var items = {};
                for (var i = 0; i < sessionStorage.length; i++) {
                    var key = sessionStorage.key(i);
                    items[key] = sessionStorage.getItem(key);
                }
                return items;
                """
                self.state.session_storage = self.driver.driver.execute_script(session_storage_script)
            except Exception as e:
                print(f"Warning: Could not capture sessionStorage: {e}")
                self.state.session_storage = {}
                
        except Exception as e:
            print(f"Warning: Could not capture full session state: {e}")
            
        return self.state
    
    def restore_session_state(self, state: Optional[SessionState] = None) -> bool:
        """Restore browser session from captured state"""
        if not self.driver.driver:
            return False
            
        target_state = state or self.state
        
        try:
            # Restore cookies
            if target_state.cookies:
                for cookie in target_state.cookies:
                    try:
                        self.driver.driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"Warning: Could not restore cookie {cookie.get('name', 'unknown')}: {e}")
            
            # Restore localStorage
            if target_state.local_storage:
                local_storage_script = """
                var items = arguments[0];
                for (var key in items) {
                    localStorage.setItem(key, items[key]);
                }
                """
                self.driver.driver.execute_script(local_storage_script, target_state.local_storage)
            
            # Restore sessionStorage
            if target_state.session_storage:
                session_storage_script = """
                var items = arguments[0];
                for (var key in items) {
                    sessionStorage.setItem(key, items[key]);
                }
                """
                self.driver.driver.execute_script(session_storage_script, target_state.session_storage)
                
            return True
            
        except Exception as e:
            print(f"Warning: Could not restore session state: {e}")
            return False
    
    def save_state_to_file(self) -> None:
        """Save session state to file for persistence"""
        try:
            state_dict = asdict(self.state)
            # Convert datetime objects to strings for JSON serialization
            state_dict['start_time'] = self.state.start_time.isoformat()
            state_dict['last_activity'] = self.state.last_activity.isoformat()
            if self.state.handover_start_time:
                state_dict['handover_start_time'] = self.state.handover_start_time.isoformat()
            if self.state.handover_timeout:
                state_dict['handover_timeout'] = self.state.handover_timeout.isoformat()
            
            with open(self.state_file, 'w') as f:
                json.dump(state_dict, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save state to file: {e}")
    
    def load_state_from_file(self, session_id: str) -> Optional[SessionState]:
        """Load session state from file"""
        state_file = Path(f"session_state_{session_id}.json")
        if not state_file.exists():
            return None
            
        try:
            with open(state_file, 'r') as f:
                state_dict = json.load(f)
            
            # Convert string dates back to datetime objects
            state_dict['start_time'] = datetime.fromisoformat(state_dict['start_time'])
            state_dict['last_activity'] = datetime.fromisoformat(state_dict['last_activity'])
            if state_dict.get('handover_start_time'):
                state_dict['handover_start_time'] = datetime.fromisoformat(state_dict['handover_start_time'])
            if state_dict.get('handover_timeout'):
                state_dict['handover_timeout'] = datetime.fromisoformat(state_dict['handover_timeout'])
            
            return SessionState(**state_dict)
            
        except Exception as e:
            print(f"Warning: Could not load state from file: {e}")
            return None
    
    def _heartbeat_monitor(self) -> None:
        """Monitor browser state during human takeover"""
        while not self._shutdown_event.is_set():
            try:
                if self.state.is_handover_active:
                    # Check for timeout
                    if (self.state.handover_timeout and 
                        datetime.now() > self.state.handover_timeout):
                        print(f"\n⏰ Handover timeout reached ({self.config.handover_timeout_minutes} minutes)")
                        print("🔄 Initiating automatic cleanup...")
                        self._trigger_callback('handover_timeout')
                        break
                    
                    # Update visual indicators
                    if self.config.visual_indicators and self.driver.driver:
                        try:
                            original_title = self.driver.driver.title
                            if not original_title.startswith("🤖"):
                                # Add automation indicator to title
                                new_title = f"🤖 PAUSED - {original_title}"
                                self.driver.driver.execute_script(f"document.title = '{new_title}';")
                        except Exception as e:
                            print(f"Warning: Could not update browser title: {e}")
                    
                    # Capture periodic state updates
                    self.capture_session_state()
                    self.save_state_to_file()
                
                # Wait for next heartbeat
                self._shutdown_event.wait(self.config.heartbeat_interval_seconds)
                
            except Exception as e:
                print(f"Warning: Heartbeat monitor error: {e}")
                time.sleep(1)
    
    def start_handover_mode(self) -> None:
        """Start human takeover mode"""
        print(f"\n{'='*80}")
        print(f"🤖 SESSION HANDOVER INITIATED")
        print(f"{'='*80}")
        
        # Capture current state
        self.capture_session_state()
        
        # Set handover state
        with self._state_lock:
            self.state.is_handover_active = True
            self.state.handover_start_time = datetime.now()
            self.state.handover_timeout = datetime.now() + timedelta(minutes=self.config.handover_timeout_minutes)
        
        # Save state
        self.save_state_to_file()
        
        # Update browser title
        if self.config.visual_indicators and self.driver.driver:
            try:
                original_title = self.driver.driver.title
                new_title = f"🤖 PAUSED - {original_title}"
                self.driver.driver.execute_script(f"document.title = '{new_title}';")
            except Exception as e:
                print(f"Warning: Could not update browser title: {e}")
        
        # Display handover message
        print(f"\n{self.config.handover_message}")
        print(f"⏰ Session will remain open for {self.config.handover_timeout_minutes} minutes")
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🆔 Session ID: {self.state.session_id}")
        print(f"{'='*80}\n")
        
        # Start heartbeat monitoring
        self._shutdown_event.clear()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_monitor, daemon=True)
        self._heartbeat_thread.start()
        
        # Trigger callback
        self._trigger_callback('handover_started', session_state=self.state)
    
    def end_handover_mode(self) -> bool:
        """End human takeover mode and restore automation"""
        print(f"\n{'='*80}")
        print(f"🤖 RESUMING AUTOMATION")
        print(f"{'='*80}")
        
        # Stop heartbeat monitoring
        self._shutdown_event.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2)
        
        # Restore browser title
        if self.config.visual_indicators and self.driver.driver:
            try:
                original_title = self.driver.driver.title
                if original_title.startswith("🤖 PAUSED - "):
                    clean_title = original_title.replace("🤖 PAUSED - ", "")
                    self.driver.driver.execute_script(f"document.title = '{clean_title}';")
            except Exception as e:
                print(f"Warning: Could not restore browser title: {e}")
        
        # Update state
        with self._state_lock:
            self.state.is_handover_active = False
            self.state.handover_start_time = None
            self.state.handover_timeout = None
        
        # Capture final state
        self.capture_session_state()
        
        print(f"\n{self.config.resume_message}")
        print(f"🕐 Resumed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Trigger callback
        self._trigger_callback('handover_ended', session_state=self.state)
        
        return True
    
    def cleanup_session(self) -> None:
        """Clean up session and close browser"""
        print(f"\n{'='*80}")
        print(f"🤖 SESSION CLEANUP")
        print(f"{'='*80}")
        
        # Stop all monitoring
        self._shutdown_event.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2)
        
        # Final state capture
        self.capture_session_state()
        self.save_state_to_file()
        
        print(f"\n{self.config.cleanup_message}")
        print(f"🕐 Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Session state saved to: {self.state_file}")
        print(f"{'='*80}\n")
        
        # Trigger callback
        self._trigger_callback('session_cleanup', session_state=self.state)
        
        # Clean up state file after a delay
        def delayed_cleanup():
            time.sleep(60)  # Wait 1 minute before cleanup
            try:
                if self.state_file.exists():
                    self.state_file.unlink()
                    print(f"🗑️  Cleaned up session state file: {self.state_file}")
            except Exception as e:
                print(f"Warning: Could not clean up state file: {e}")
        
        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()
    
    def is_under_human_control(self) -> bool:
        """Check if browser is currently under human control"""
        return self.state.is_handover_active
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            'session_id': self.state.session_id,
            'start_time': self.state.start_time.isoformat(),
            'last_activity': self.state.last_activity.isoformat(),
            'is_handover_active': self.state.is_handover_active,
            'handover_start_time': self.state.handover_start_time.isoformat() if self.state.handover_start_time else None,
            'handover_timeout': self.state.handover_timeout.isoformat() if self.state.handover_timeout else None,
            'current_url': self.state.current_url,
            'browser_title': self.state.browser_title,
            'cookies_count': len(self.state.cookies),
            'local_storage_count': len(self.state.local_storage),
            'session_storage_count': len(self.state.session_storage)
        }
    
    def detect_human_activity(self) -> bool:
        """Detect if there has been recent human activity"""
        if not self.driver.driver:
            return False
            
        try:
            # Check for recent mouse movements or keyboard activity
            # This is a simple heuristic - in practice, you might want more sophisticated detection
            
            # Check if URL has changed (indicating navigation)
            current_url = self.driver.driver.current_url
            if current_url != self.state.current_url:
                self.state.last_activity = datetime.now()
                return True
            
            # Check if page title has changed
            current_title = self.driver.driver.title
            if current_title != self.state.browser_title:
                self.state.last_activity = datetime.now()
                return True
            
            return False
            
        except Exception as e:
            print(f"Warning: Could not detect human activity: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    from src.drivers.browser_selenium import SeleniumCanvasDriver
    
    driver = SeleniumCanvasDriver()
    session_manager = SessionManager(driver)
    
    # Register callbacks
    session_manager.register_callback('handover_started', lambda session_state: print("Handover started!"))
    session_manager.register_callback('handover_ended', lambda session_state: print("Handover ended!"))
    session_manager.register_callback('handover_timeout', lambda: print("Handover timeout!"))
    
    print("Session Manager initialized")
    print(f"Session ID: {session_manager.state.session_id}")
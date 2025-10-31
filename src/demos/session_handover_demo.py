#!/usr/bin/env python3
"""
Session Handover Demo Script

This script demonstrates the browser session handover functionality for the 
Floor and Decor automation script. It shows how to:

1. Initialize automation with session management
2. Run automation with optional human takeover points
3. Pause automation for human interaction
4. Resume automation after human takeover
5. Handle session persistence and cleanup

Usage:
    python src/demos/session_handover_demo.py
"""

import os
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.web_agent import VisionWebAgent, AgentConfig
from src.agent.session_manager import SessionManager, SessionConfig
from src.drivers.browser_selenium import SeleniumCanvasDriver


def demo_basic_handover():
    """Demonstrate basic session handover functionality"""
    print("\n" + "="*80)
    print("🎯 DEMO 1: Basic Session Handover")
    print("="*80)
    
    # Create agent with session management
    agent = VisionWebAgent()
    
    # Configure session for 2-minute handover timeout
    session_config = SessionConfig(
        handover_timeout_minutes=2,
        visual_indicators=True,
        handover_message="🤖 Automation paused for manual review. Please check the cart contents and make any necessary adjustments."
    )
    
    try:
        # Run automation with handover after completion
        print("🚀 Starting automation with handover after completion...")
        
        result = agent.run_with_handover(
            start_url="https://www.flooranddecor.com",
            goal="Navigate to the shopping cart to review items",
            cfg=AgentConfig(max_steps=2, log_dir="logs/demo1"),
            session_config=session_config,
            handover_after_steps='all'  # Handover after automation completes
        )
        
        print(f"✅ Automation completed. Status: {result['status']}")
        print(f"📊 Steps executed: {len(result['steps'])}")
        
        if 'handover_info' in result:
            print(f"🤝 Handover info: {result['handover_info']}")
        
        # Check if browser is under human control
        if agent.is_under_human_control():
            print("\n🔄 Browser is now under human control!")
            print("💡 You can now interact with the browser manually.")
            print("⏰ The session will timeout in 2 minutes if no activity.")
            print("\n📝 To resume automation, call: agent.resume_from_human_takeover()")
            print("🗑️  To cleanup session, call: agent.cleanup_session()")
            
            # Simulate human interaction time
            print("\n⏳ Simulating human interaction (10 seconds)...")
            time.sleep(10)
            
            # Resume automation
            print("\n🔄 Resuming automation...")
            success = agent.resume_from_human_takeover()
            if success:
                print("✅ Successfully resumed automation")
            else:
                print("❌ Failed to resume automation")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        agent.cleanup_session()


def demo_step_handover():
    """Demonstrate handover at specific step"""
    print("\n" + "="*80)
    print("🎯 DEMO 2: Step-based Handover")
    print("="*80)
    
    # Create agent
    agent = VisionWebAgent()
    
    # Configure session
    session_config = SessionConfig(
        handover_timeout_minutes=1,
        visual_indicators=True,
        handover_message="🤖 Automation paused at step 1. Please review the current page and make any adjustments."
    )
    
    try:
        # Run automation with handover after step 1
        print("🚀 Starting automation with handover after step 1...")
        
        result = agent.run_with_handover(
            start_url="https://www.flooranddecor.com",
            goal="Navigate to a product category page",
            cfg=AgentConfig(max_steps=3, log_dir="logs/demo2"),
            session_config=session_config,
            handover_after_steps=1  # Handover after step 1
        )
        
        print(f"✅ Automation paused. Status: {result['status']}")
        print(f"📊 Steps executed: {len(result['steps'])}")
        
        if 'handover_info' in result:
            print(f"🤝 Handover info: {result['handover_info']}")
        
        if agent.is_under_human_control():
            print("\n🔄 Browser paused at step 1 for human review!")
            print("💡 Review the current page and make any necessary changes.")
            
            # Simulate human review
            print("\n⏳ Simulating human review (5 seconds)...")
            time.sleep(5)
            
            # Resume automation
            print("\n🔄 Resuming automation from step 2...")
            success = agent.resume_from_human_takeover()
            if success:
                print("✅ Successfully resumed automation")
                
                # Continue with remaining steps (would need to implement continuation logic)
                print("📝 In a real scenario, automation would continue from step 2")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        agent.cleanup_session()


def demo_manual_handover():
    """Demonstrate manual handover control"""
    print("\n" + "="*80)
    print("🎯 DEMO 3: Manual Handover Control")
    print("="*80)
    
    # Create driver and session manager directly
    driver = SeleniumCanvasDriver()
    session_manager = SessionManager(driver)
    
    try:
        # Open browser
        print("🚀 Opening browser...")
        driver.open("https://www.flooranddecor.com")
        
        # Register session callbacks
        def on_handover_started(session_state):
            print(f"🤝 Handover started! Session: {session_state.session_id}")
        
        def on_handover_ended(session_state):
            print(f"🔄 Handover ended! Session: {session_state.session_id}")
        
        session_manager.register_callback('handover_started', on_handover_started)
        session_manager.register_callback('handover_ended', on_handover_ended)
        
        # Run some automation steps manually
        print("🖱️  Performing manual automation steps...")
        time.sleep(2)
        
        # Start handover mode
        print("\n🤝 Starting manual handover mode...")
        session_manager.start_handover_mode()
        
        # Check session info
        session_info = session_manager.get_session_info()
        print(f"📊 Session info: {session_info}")
        
        # Simulate human interaction
        print("\n⏳ Simulating human interaction (8 seconds)...")
        time.sleep(8)
        
        # End handover mode
        print("\n🔄 Ending handover mode...")
        session_manager.end_handover_mode()
        
        # Get final session info
        final_info = session_manager.get_session_info()
        print(f"📊 Final session info: {final_info}")
        
        # Cleanup
        print("\n🧹 Cleaning up session...")
        session_manager.cleanup_session()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        if driver.driver:
            driver.force_close()


def demo_browser_persistence():
    """Demonstrate browser persistence features"""
    print("\n" + "="*80)
    print("🎯 DEMO 4: Browser Persistence Features")
    print("="*80)
    
    driver = SeleniumCanvasDriver()
    
    try:
        # Open browser
        print("🚀 Opening browser...")
        driver.open("https://www.flooranddecor.com")
        
        # Show initial status
        initial_status = driver.get_browser_status()
        print(f"📊 Initial browser status: {initial_status}")
        
        # Install human activity monitors
        print("\n📡 Installing human activity monitors...")
        driver.install_human_activity_monitors()
        
        # Set browser to keep alive
        print("\n🔄 Setting browser to keep alive...")
        driver.set_keep_alive(True)
        
        # Show updated status
        updated_status = driver.get_browser_status()
        print(f"📊 Updated browser status: {updated_status}")
        
        # Keep browser alive with message
        print("\n💬 Keeping browser alive with user message...")
        driver.keep_browser_alive(
            "🤖 Browser session preserved for manual review.\n"
            "Please review the current page and make any necessary changes.\n"
            "The browser will remain open for your interaction."
        )
        
        # Simulate human activity detection
        print("\n⏳ Simulating human activity (6 seconds)...")
        time.sleep(6)
        
        # Check for human control
        human_detected = driver.detect_human_control()
        print(f"👤 Human control detected: {human_detected}")
        
        # Take a screenshot
        print("\n📸 Taking screenshot...")
        screenshot = driver.take_screenshot("logs/demo4_screenshot.png")
        print(f"📸 Screenshot captured: {len(screenshot)} bytes")
        
        # Get page source
        print("\n📄 Getting page source...")
        page_source = driver.get_page_source()
        print(f"📄 Page source length: {len(page_source)} characters")
        
        # Final status check
        final_status = driver.get_browser_status()
        print(f"📊 Final browser status: {final_status}")
        
        # Force close
        print("\n🔄 Force closing browser...")
        driver.force_close()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        if driver.driver:
            driver.force_close()


def demo_session_persistence():
    """Demonstrate session state persistence"""
    print("\n" + "="*80)
    print("🎯 DEMO 5: Session State Persistence")
    print("="*80)
    
    driver = SeleniumCanvasDriver()
    session_manager = SessionManager(driver)
    
    try:
        # Open browser and navigate
        print("🚀 Opening browser and navigating...")
        driver.open("https://www.flooranddecor.com")
        
        # Capture initial state
        print("\n📸 Capturing initial session state...")
        initial_state = session_manager.capture_session_state()
        print(f"📊 Initial state - URL: {initial_state.current_url}")
        print(f"📊 Initial state - Title: {initial_state.browser_title}")
        print(f"📊 Initial state - Cookies: {len(initial_state.cookies)}")
        
        # Save state to file
        print("\n💾 Saving state to file...")
        session_manager.save_state_to_file()
        
        # Simulate some changes (in real scenario, user would interact)
        print("\n⏳ Simulating session changes (3 seconds)...")
        time.sleep(3)
        
        # Capture updated state
        print("\n📸 Capturing updated session state...")
        updated_state = session_manager.capture_session_state()
        print(f"📊 Updated state - URL: {updated_state.current_url}")
        print(f"📊 Updated state - Title: {updated_state.browser_title}")
        
        # Save updated state
        print("\n💾 Saving updated state...")
        session_manager.save_state_to_file()
        
        # Get session info
        session_info = session_manager.get_session_info()
        print(f"📊 Session info: {session_info}")
        
        # Cleanup
        print("\n🧹 Cleaning up...")
        session_manager.cleanup_session()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        if driver.driver:
            driver.force_close()


def main():
    """Run all demos"""
    print("🎭 Browser Session Handover Demo")
    print("="*80)
    print("This demo showcases the browser session handover functionality")
    print("for the Floor and Decor automation script.")
    print("="*80)
    
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    demos = [
        ("Basic Handover", demo_basic_handover),
        ("Step-based Handover", demo_step_handover),
        ("Manual Handover Control", demo_manual_handover),
        ("Browser Persistence", demo_browser_persistence),
        ("Session State Persistence", demo_session_persistence),
    ]
    
    for i, (name, demo_func) in enumerate(demos, 1):
        try:
            print(f"\n🎬 Running Demo {i}/{len(demos)}: {name}")
            demo_func()
            
            if i < len(demos):
                print(f"\n⏳ Waiting 3 seconds before next demo...")
                time.sleep(3)
                
        except KeyboardInterrupt:
            print(f"\n⏹️  Demo interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Demo {i} failed: {e}")
            continue
    
    print("\n" + "="*80)
    print("🎉 All demos completed!")
    print("="*80)
    print("\n📚 Key Features Demonstrated:")
    print("✅ Session state capture and restoration")
    print("✅ Browser persistence during human takeover")
    print("✅ Visual indicators for automation state")
    print("✅ Human activity detection")
    print("✅ Timeout management")
    print("✅ Clean handoff notifications")
    print("✅ Session cleanup and recovery")
    print("\n💡 Check the 'logs' directory for screenshots and session data")


if __name__ == "__main__":
    main()
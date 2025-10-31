"""
Simple test without Chrome profile - just test the keep-alive functionality.
"""
import os
import sys
import time
sys.path.insert(0, 'C:/Agent-S-Redfinger')

# Don't use Chrome profile for this test
os.environ.pop("CHROME_PROFILE_DIR", None)

from src.agent.web_agent import VisionWebAgent, AgentConfig

def simple_test():
    """Simple test without Chrome profile"""
    
    print("\n" + "="*80)
    print("🧪 SIMPLE BROWSER HANDOVER TEST")
    print("="*80)
    
    # Enable browser persistence
    os.environ["AGENT_KEEP_BROWSER_OPEN"] = "true"
    
    print("\n✅ AGENT_KEEP_BROWSER_OPEN=true")
    print("🚀 Opening browser in 2 seconds...")
    print("   (Using fresh Chrome session, no profile)")
    time.sleep(2)
    
    # Initialize agent without profile
    agent = VisionWebAgent(profile_dir=None)
    
    try:
        # Run a simple navigation test
        print("\n📍 Opening Floor & Decor website...")
        result = agent.run(
            start_url="https://www.flooranddecor.com",
            goal="Navigate to the site",
            cfg=AgentConfig(
                provider="none",  # Use DOM fallback
                max_steps=1,
                step_delay_s=2.0,
                stop_on_navigation=False
            )
        )
        
        print("\n" + "="*80)
        print("✅ TEST COMPLETE - AUTOMATION FINISHED")
        print("="*80)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Steps: {len(result.get('steps', []))}")
        
        if agent.drv.driver:
            print(f"Current URL: {agent.drv.driver.current_url}")
            print("\n🎉 SUCCESS! Browser is OPEN and ready!")
            print("   The automation has finished, but the browser stays open.")
            print("   You can now manually interact with the page.")
            print("   Close the browser window manually when done.")
        
        print("\n⏸️  Script will exit in 10 seconds...")
        print("   Watch the browser - it should STAY OPEN after script exits!")
        time.sleep(10)
        
        print("\n👋 Script exiting NOW. Browser should remain open!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simple_test()

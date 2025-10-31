"""
Quick automated test - no user input required.
Tests browser handover in non-interactive mode.
"""
import os
import sys
import time
sys.path.insert(0, 'C:/Agent-S-Redfinger')

from src.agent.web_agent import VisionWebAgent, AgentConfig

def quick_test():
    """Quick automated test of browser handover"""
    
    print("\n" + "="*80)
    print("🧪 QUICK BROWSER HANDOVER TEST (Automated)")
    print("="*80)
    
    # Enable browser persistence
    os.environ["AGENT_KEEP_BROWSER_OPEN"] = "true"
    
    print("\n✅ AGENT_KEEP_BROWSER_OPEN=true")
    print("🚀 Starting test in 3 seconds...")
    time.sleep(3)
    
    # Initialize agent
    agent = VisionWebAgent()
    
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
        print("✅ TEST COMPLETE")
        print("="*80)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Steps: {len(result.get('steps', []))}")
        
        if agent.drv.driver:
            print(f"Current URL: {agent.drv.driver.current_url}")
            print("\n🎉 Browser is OPEN and ready!")
            print("   You can now manually interact with the browser.")
            print("   The browser will stay open after this script exits.")
        
        print("\n⏸️  Waiting 5 seconds before exit...")
        time.sleep(5)
        
        print("\n👋 Script exiting. Browser should remain open!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    quick_test()

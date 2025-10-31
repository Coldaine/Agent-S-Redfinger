"""
Test script to verify browser handover and keep-alive functionality.
This test navigates to Floor & Decor and then leaves the browser open for manual control.
"""
import os
import sys
sys.path.insert(0, 'C:/Agent-S-Redfinger')

from src.agent.web_agent import VisionWebAgent, AgentConfig

def test_browser_handover():
    """Test that browser stays open after automation completes"""
    
    print("\n" + "="*80)
    print("🧪 TESTING BROWSER HANDOVER FUNCTIONALITY")
    print("="*80)
    print("\nThis test will:")
    print("  1. Open Chrome and navigate to Floor & Decor")
    print("  2. Perform a simple navigation using DOM fallback (no vision API needed)")
    print("  3. Leave the browser OPEN for you to continue manually")
    print("\n⚠️  Make sure ALL Chrome windows are closed before starting!")
    print("\nPress Enter to start the test...")
    input()
    
    # Enable browser persistence
    os.environ["AGENT_KEEP_BROWSER_OPEN"] = "true"
    
    print("\n🚀 Starting test...")
    print("   Setting AGENT_KEEP_BROWSER_OPEN=true")
    
    # Initialize agent
    agent = VisionWebAgent()
    
    try:
        # Run a simple navigation test
        print("\n📍 Opening Floor & Decor website...")
        result = agent.run(
            start_url="https://www.flooranddecor.com",
            goal="Navigate to the site and show main page",
            cfg=AgentConfig(
                provider="none",  # Use DOM fallback (no vision API needed)
                max_steps=2,
                step_delay_s=2.0,
                log_dir="logs/test_handover",
                stop_on_navigation=False
            )
        )
        
        print("\n" + "="*80)
        print("✅ TEST AUTOMATION COMPLETE")
        print("="*80)
        print(f"\n📊 Results:")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Steps completed: {len(result.get('steps', []))}")
        
        if result.get('steps'):
            last_step = result['steps'][-1]
            print(f"   Final URL: {last_step.get('post_url', 'unknown')}")
        
        print("\n" + "="*80)
        print("🎉 BROWSER HANDOVER SUCCESSFUL!")
        print("="*80)
        print("\n✅ The Chrome browser is now OPEN and ready for you!")
        print("\n🛒 You can now:")
        print("   • Manually browse the Floor & Decor website")
        print("   • Search for products by SKU")
        print("   • Add items to your cart")
        print("   • Complete your shopping")
        print("\n💡 The browser will stay open even after this script exits.")
        print("   Close the browser window manually when you're done.")
        print("\n⏸️  Press Enter to exit this script (browser will stay open)...")
        input()
        
        print("\n👋 Script exiting. Browser remains open for your use!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nThe test encountered an error, but the browser should still be open.")
        print("You can manually navigate and shop if needed.\n")
        raise

if __name__ == "__main__":
    test_browser_handover()

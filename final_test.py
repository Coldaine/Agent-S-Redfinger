"""
Final test - explicitly bypass profile and test handover
"""
import os
import sys
import time
sys.path.insert(0, 'C:/Agent-S-Redfinger')

# Clear any Chrome profile settings
for key in list(os.environ.keys()):
    if 'CHROME' in key or 'PROFILE' in key:
        del os.environ[key]

from src.drivers.browser_selenium import SeleniumCanvasDriver

def final_test():
    """Test browser handover with explicit no-profile driver"""
    
    print("\n" + "="*80)
    print("🧪 FINAL BROWSER HANDOVER TEST")
    print("="*80 + "\n")
    
    # Enable browser persistence
    os.environ["AGENT_KEEP_BROWSER_OPEN"] = "true"
    
    print("✅ AGENT_KEEP_BROWSER_OPEN=true")
    print("📍 Creating fresh Chrome session (no profile)...")
    
    # Create driver with explicit no profile
    driver = SeleniumCanvasDriver(browser="chrome", profile_dir=None)
    driver.set_keep_alive(True)
    
    try:
        print("\n🚀 Opening Floor & Decor website...")
        driver.open("https://www.flooranddecor.com")
        
        print("✅ Page loaded!")
        print(f"   URL: {driver.driver.current_url if driver.driver else 'N/A'}")
        
        print("\n⏸️  Waiting 5 seconds...")
        time.sleep(5)
        
        print("\n" + "="*80)
        print("🎉 TEST COMPLETE!")
        print("="*80)
        print("\n✅ Calling driver.close() with keep-alive enabled...")
        print("   Browser should STAY OPEN...")
        
        driver.close()
        
        print("\n✅ driver.close() called!")
        print("🛑 Not closing Chrome (keep-open enabled). Browser remains available for you.")
        print("\n⏸️  Script will exit in 5 seconds...")
        print("   Watch the browser - it should STAY OPEN!")
        time.sleep(5)
        
        print("\n👋 Script exiting NOW!")
        print("   Check if the browser is still open...")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    final_test()

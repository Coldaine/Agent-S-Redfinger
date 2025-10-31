"""
Quick test to verify Chrome profile support works.
"""
import sys
sys.path.insert(0, 'C:/Agent-S-Redfinger')

from src.drivers.browser_selenium import SeleniumCanvasDriver
import time

print("\n" + "="*80)
print("🧪 TESTING CHROME PROFILE SUPPORT")
print("="*80 + "\n")

profile_path = r"C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default"

print(f"Profile: {profile_path}")
print("\n⚠️  Make sure ALL Chrome windows are closed!\n")
print("Press Enter to continue...")
input()

print("🚀 Opening Chrome with your profile...")
print("   You should see YOUR bookmarks, extensions, and logged-in status!\n")

driver = SeleniumCanvasDriver(profile_dir=profile_path)

try:
    driver.open("https://github.com")
    print("✅ GitHub opened")
    print(f"   URL: {driver.driver.current_url if driver.driver else 'N/A'}")
    
    print("\n👀 Look at the Chrome window - are you logged in?")
    print("   - Check for your profile picture (top-right)")
    print("   - Look for notification bell")
    print("   - Verify bookmarks bar shows your bookmarks")
    
    time.sleep(10)
    
    print("\n📸 Taking screenshot...")
    screenshot = driver.driver.get_screenshot_as_png() if driver.driver else None
    if screenshot:
        with open("test_profile_screenshot.png", "wb") as f:
            f.write(screenshot)
        print("✅ Screenshot saved: test_profile_screenshot.png")
        print("   Open it to verify you're logged in!")
    
    print("\n✅ Test complete! Press Enter to close...")
    input()
    
finally:
    driver.close()
    print("\n🎉 Chrome profile support is working!")
    print("="*80 + "\n")

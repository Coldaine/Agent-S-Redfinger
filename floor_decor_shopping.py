"""
Floor & Decor Shopping Automation Script
Adds items to cart and hands over browser control for manual checkout.
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
import logging
sys.path.insert(0, 'C:/Agent-S-Redfinger')

from src.agent.web_agent import VisionWebAgent, AgentConfig
from src.agent.session_manager import SessionConfig
from selenium.webdriver.common.by import By

# Shopping list with all required items
SHOPPING_LIST = [
    {
        "sku": "100507714",
        "quantity": 400,
        "name": "La Belle Air Ceramic Polished Tile, Blue 3x12",
        "coverage": "100 sqft",
        "unit": "pieces"
    },
    {
        "sku": "101055184",
        "quantity": 3,
        "name": "Hawkins Ivory Porcelain Tile, 12x24",
        "coverage": "54 sqft",
        "unit": "boxes"
    },
    {
        "sku": "101068724",
        "quantity": 3,
        "name": "Blue Celeste Thassos Bianco Carrara Fan Honed Marble Mosaic, 12x12",
        "coverage": "2.76 sqft",
        "unit": "pieces"
    },
    {
        "sku": "101155638",
        "quantity": 4,
        "name": "Andros White Matte Ceramic Tile, 12x24",
        "coverage": "61 sqft",
        "unit": "boxes"
    },
    {
        "sku": "100946920",
        "quantity": 3,
        "name": "Basalt Nova Noir Honed Mosaic, 10x12",
        "coverage": "2.52 sqft",
        "unit": "pieces"
    },
    {
        "sku": "100999903",
        "quantity": 363,
        "name": "Artisan Noir Matte Ceramic Tile, 2x16",
        "coverage": "100 sqft",
        "unit": "pieces"
    },
    {
        "sku": "101174019",
        "quantity": 24,
        "name": "Della Bianca Matte Porcelain Tile, 24x24",
        "coverage": "320 sqft",
        "unit": "boxes"
    },
    {
        "sku": "100966522",
        "quantity": 164,
        "name": "Unglazed Charcoal Herringbone Porcelain Mosaic",
        "coverage": "100 sqft",
        "unit": "pieces"
    }
]

def print_shopping_list():
    """Display the shopping list to the user"""
    print("\n" + "="*80)
    print("🛒 FLOOR & DECOR SHOPPING LIST")
    print("="*80)
    for i, item in enumerate(SHOPPING_LIST, 1):
        print(f"\n{i}. {item['name']}")
        print(f"   SKU: {item['sku']}")
        print(f"   Quantity: {item['quantity']} {item['unit']}")
        print(f"   Coverage: {item['coverage']}")
    print("\n" + "="*80)

def add_items_to_cart():
    """
    Add all items from the shopping list to Floor & Decor cart
    and hand over browser control for manual review and checkout.
    """
    # --- Per-session log directory & file logging (tee stdout/stderr) ---
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    session_dir = Path(f"logs/shopping_{ts}")
    session_dir.mkdir(parents=True, exist_ok=True)

    class _Tee:
        def __init__(self, *streams):
            self._streams = streams
        def write(self, data):
            for s in self._streams:
                try:
                    s.write(data)
                except Exception:
                    pass
        def flush(self):
            for s in self._streams:
                try:
                    s.flush()
                except Exception:
                    pass

    # Set up logging.Logger (also useful for external tools)
    log_file = session_dir / "session.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.__stdout__),
        ],
    )
    logger = logging.getLogger("floor_decor_shopping")
    # Tee all prints to the same file for complete capture
    _orig_out, _orig_err = sys.stdout, sys.stderr
    sys.stdout = _Tee(sys.__stdout__, open(log_file, "a", encoding="utf-8"))
    sys.stderr = _Tee(sys.__stderr__, open(log_file, "a", encoding="utf-8"))

    # Persist session metadata for later debugging
    try:
        meta = {
            "started_at": datetime.now().isoformat(),
            "provider": os.getenv("VISION_PROVIDER", "openai"),
            "model": os.getenv("VISION_MODEL", "gpt-5"),
            "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "zai_base_url": os.getenv("ZAI_BASE_URL", "https://api.bigmodel.org"),
            "chrome_profile_dir": os.getenv("CHROME_PROFILE_DIR"),
            "agent_keep_open": os.getenv("AGENT_KEEP_BROWSER_OPEN"),
            "env": {
                "os": os.name,
                "pwd": str(Path.cwd()),
                "python": sys.version,
            },
        }
        with open(session_dir / "session_meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write session_meta.json: {e}")

    print("\n" + "="*80)
    print("🤖 FLOOR & DECOR SHOPPING AUTOMATION")
    print("="*80)
    print(f"\n⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show shopping list
    print_shopping_list()
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("   • Make sure ALL Chrome windows are closed before starting")
    print("   • This will use your OpenAI API for vision-guided automation")
    print("   • The browser will stay open for you to complete checkout")
    print("   • You'll be able to review and adjust quantities manually")
    
    # Check for API key
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Determine provider/model early for logging consistency
    model = os.getenv("VISION_MODEL", "gpt-5-mini")
    provider = os.getenv("VISION_PROVIDER", "openai").lower()

    if not api_key and provider == "openai":
        print("\n❌ ERROR: OPENAI_API_KEY not found in environment!")
        print("   Set your API key in .env file or environment variable.")
        print("   Falling back to DOM-based navigation (less reliable).")
        provider = "none"
    else:
        if provider == "openai":
            tail = (api_key or "")[-4:]
            print(f"\n✅ OpenAI API key found (ends with: ...{tail})")
        print(f"🔧 Vision provider: {provider}")
        print(f"🧠 Vision model: {model}")
    
    print("\nPress Enter to start automation, or Ctrl+C to cancel...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.\n")
        return
    
    # Enable browser persistence
    os.environ["AGENT_KEEP_BROWSER_OPEN"] = "true"
    
    # Initialize agent
    agent = VisionWebAgent()
    
    # Configure session for handover
    session_config = SessionConfig(
        handover_timeout_minutes=60,
        visual_indicators=True,
        handover_message="🛒 Automation complete. Review your cart and complete checkout when ready."
    )
    
    print("\n🚀 Starting automation...")
    print(f"📦 Items to process: {len(SHOPPING_LIST)}")
    print("="*80)
    
    results = []
    
    try:
        # Navigate to Floor & Decor
        print("\n[STEP 0] Opening Floor & Decor website...")
        agent.drv.set_keep_alive(True)
        agent.drv.open("https://www.flooranddecor.com")
        time.sleep(3)  # Let page fully load
        
        print("✅ Website loaded")

        # Optional: explicit login with provided credentials
        fd_email = os.getenv("FLOOR_DECOR_EMAIL")
        fd_password = os.getenv("FLOOR_DECOR_PASSWORD")
        if fd_email and fd_password:
            print("\n[STEP 0a] Attempting account sign-in...")
            if _login_floor_and_decor(agent, fd_email, fd_password):
                print("✅ Signed in to Floor & Decor account")
            else:
                print("⚠️  Could not verify sign-in. Continuing without explicit login.")
        
        # Process each item
        for i, item in enumerate(SHOPPING_LIST, 1):
            print(f"\n{'─'*80}")
            print(f"[ITEM {i}/{len(SHOPPING_LIST)}] Processing: {item['name']}")
            print(f"{'─'*80}")
            print(f"   SKU: {item['sku']}")
            print(f"   Quantity: {item['quantity']} {item['unit']}")
            
            # Create goal for this item
            goal = f"Search for SKU {item['sku']}, find the product, and add {item['quantity']} {item['unit']} to cart"
            
            try:
                # Run automation for this item
                print(f"\n   🔍 Searching for product...")
                
                result = agent.run(
                    start_url=agent.drv.driver.current_url if agent.drv.driver else "https://www.flooranddecor.com",
                    goal=goal,
                    cfg=AgentConfig(
                        provider=provider,
                        model=model,
                        max_steps=15,  # Allow enough steps for search, selection, quantity, add to cart
                        step_delay_s=2.5,  # Give pages time to load
                        log_dir=f"{session_dir}/item_{i}",
                        stop_on_navigation=False  # Keep going through multiple pages
                    )
                )
                
                status = result.get('status', 'unknown')
                steps = len(result.get('steps', []))
                
                print(f"\n   ✅ Item processed")
                print(f"      Status: {status}")
                print(f"      Steps: {steps}")
                
                results.append({
                    "item": item,
                    "status": status,
                    "steps": steps,
                    "success": status in ['ok', 'navigated']
                })
                
                # Brief pause between items
                print(f"\n   ⏸️  Pausing 3 seconds before next item...")
                time.sleep(3)
                
            except Exception as e:
                print(f"\n   ❌ ERROR processing item: {e}")
                results.append({
                    "item": item,
                    "status": "error",
                    "error": str(e),
                    "success": False
                })
                
                # Continue with next item
                print(f"   ⏭️  Continuing with next item...")
                time.sleep(2)
        
        # All items processed - show summary
        print("\n" + "="*80)
        print("🎉 AUTOMATION COMPLETE!")
        print("="*80)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total items: {len(SHOPPING_LIST)}")
        successful = sum(1 for r in results if r.get('success', False))
        print(f"   Successful: {successful}")
        print(f"   Failed: {len(SHOPPING_LIST) - successful}")
        
        if successful < len(SHOPPING_LIST):
            print(f"\n⚠️  Some items may need manual attention:")
            for r in results:
                if not r.get('success', False):
                    print(f"      • {r['item']['name']} (SKU: {r['item']['sku']})")
        
        print("\n" + "="*80)
        print("🤝 HANDING OVER BROWSER CONTROL")
        print("="*80)
        
        # Hand over control with session management
        print("\n🔄 Preparing browser for manual control...")
        agent.pause_for_human_takeover(session_config)
        
        print("\n✅ Browser is now under YOUR control!")
        print("\n🛒 NEXT STEPS:")
        print("   1. Review all items in your cart")
        print("   2. Adjust quantities if needed")
        print("   3. Manually add any items that failed automation")
        print("   4. Verify coverage calculations")
        print("   5. Proceed to checkout when ready")
        
        print("\n💡 TIPS:")
        print("   • The browser will stay open indefinitely")
        print("   • Your session is saved and can be resumed")
        print("   • Close the browser manually when finished")
        
        print("\n⏸️  Press Enter to exit this script (browser stays open)...")
        input()
        
        print("\n👋 Script exiting. Browser remains open for your shopping!")
        print("="*80 + "\n")
        
        return results
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user!")
        print("   Browser will remain open for manual control.")
        print("   Close manually when done.\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        print("\n   The browser should still be open.")
        print("   You can complete shopping manually.")
        print("   Close browser when done.\n")
        raise
    finally:
        # Restore stdout/stderr if possible
        try:
            sys.stdout = _orig_out
            sys.stderr = _orig_err
        except Exception:
            pass

def _login_floor_and_decor(agent: VisionWebAgent, email: str, password: str) -> bool:
    """Log into Floor & Decor using explicit credentials.

    Strategy:
    - Try a set of known login URLs; fall back to home Sign In link if needed
    - Fill email/password via robust selectors
    - Click the Sign In / Log In button and verify by checking account UI
    """
    drv = agent.drv.driver
    if not drv:
        return False

    def try_go(url: str) -> bool:
        try:
            agent.drv.goto(url)
            time.sleep(2.0)
            return True
        except Exception:
            return False

    # Try known login endpoints (Demandware/SC) in order
    login_urls = [
        "https://www.flooranddecor.com/account",
        "https://www.flooranddecor.com/login",
        "https://www.flooranddecor.com/on/demandware.store/Sites-flooranddecor-Site/en_US/Login-Show",
    ]

    reached_login = False
    for u in login_urls:
        if try_go(u):
            # Heuristic: if we can find email/password inputs, we're on a login page
            if _fill_login_fields_if_present(agent, email, password, dry_run=True):
                reached_login = True
                break
    if not reached_login:
        # Try clicking a Sign In link from the homepage header
        try:
            agent.drv.goto("https://www.flooranddecor.com")
            time.sleep(2.0)
            # Try common XPaths for a sign in link/button
            candidates = [
                "//a[contains(translate(., 'SIGNINLOGACCOUNT', 'signinlogaccount'), 'sign in') or contains(translate(., 'SIGNINLOGACCOUNT', 'signinlogaccount'), 'login') or contains(translate(., 'MY ACCOUNT', 'my account'), 'my account')]",
                "//button[contains(translate(., 'SIGNINLOGACCOUNT', 'signinlogaccount'), 'sign in') or contains(translate(., 'SIGNINLOGACCOUNT', 'signinlogaccount'), 'login')]",
                "//a[contains(@href, 'Login') or contains(@href, 'login') or contains(@href, 'account')]",
            ]
            clicked = False
            for xp in candidates:
                try:
                    el = drv.find_element(By.XPATH, xp)
                    el.click()
                    clicked = True
                    break
                except Exception:
                    continue
            if clicked:
                time.sleep(2.5)
                reached_login = True
        except Exception:
            pass

    # Fill and submit if on login page/modal
    if not _fill_login_fields_if_present(agent, email, password, dry_run=False):
        return False

    # Click submit/login button
    submit_xpaths = [
        "//button[@type='submit']",
        "//button[contains(translate(., 'SIGNINLOGIN', 'signinlogin'), 'sign in') or contains(translate(., 'SIGNINLOGIN', 'signinlogin'), 'log in') or contains(translate(., 'SIGNINLOGIN', 'signinlogin'), 'login')]",
        "//input[@type='submit']",
    ]
    clicked_submit = False
    for xp in submit_xpaths:
        try:
            btn = drv.find_element(By.XPATH, xp)
            btn.click()
            clicked_submit = True
            break
        except Exception:
            continue
    if not clicked_submit:
        return False

    # Wait and verify login by checking for absence of Sign In and presence of account/dashboard/cart
    time.sleep(4.0)
    try:
        # If a logout link appears, we are logged in
        logout = drv.find_elements(By.XPATH, "//a[contains(translate(., 'LOGOUTSIGNOUT', 'logoutsignout'), 'logout') or contains(translate(., 'LOGOUTSIGNOUT', 'logoutsignout'), 'sign out')]")
        if logout:
            return True
        # Check if Sign In link disappeared
        signin = drv.find_elements(By.XPATH, "//a[contains(translate(., 'SIGNIN', 'signin'), 'sign in')]")
        if not signin:
            return True
    except Exception:
        pass
    return False

def _fill_login_fields_if_present(agent: VisionWebAgent, email: str, password: str, dry_run: bool) -> bool:
    """Try to locate email/password inputs. If dry_run=True, only detect; else fill."""
    drv = agent.drv.driver
    if not drv:
        return False
    try:
        # Try multiple selectors for robustness
        email_candidates = [
            "//input[@type='email']",
            "//input[contains(translate(@name, 'EMAIL', 'email'), 'email')]",
            "//input[contains(translate(@id, 'EMAIL', 'email'), 'email')]",
        ]
        pass_candidates = [
            "//input[@type='password']",
            "//input[contains(translate(@name, 'PASS', 'pass'), 'pass')]",
            "//input[contains(translate(@id, 'PASS', 'pass'), 'pass')]",
        ]
        email_el = None
        for xp in email_candidates:
            els = drv.find_elements(By.XPATH, xp)
            if els:
                email_el = els[0]
                break
        pass_el = None
        for xp in pass_candidates:
            els = drv.find_elements(By.XPATH, xp)
            if els:
                pass_el = els[0]
                break
        if not email_el or not pass_el:
            return False
        if dry_run:
            return True
        email_el.clear()
        email_el.send_keys(email)
        time.sleep(0.2)
        pass_el.clear()
        pass_el.send_keys(password)
        time.sleep(0.2)
        return True
    except Exception:
        return False

if __name__ == "__main__":
    try:
        results = add_items_to_cart()
        
        if results:
            # Show final summary
            print("\n📋 FINAL RESULTS:")
            for i, r in enumerate(results, 1):
                status_icon = "✅" if r.get('success') else "❌"
                print(f"{status_icon} {i}. {r['item']['name']} - {r['status']}")
        
    except KeyboardInterrupt:
        print("\n❌ Cancelled.\n")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")

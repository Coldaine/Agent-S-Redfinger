"""
Comprehensive test suite for the vision-guided web agent.
Runs 6 diverse test cases to validate end-to-end functionality.
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

from src.agent.web_agent import VisionWebAgent, AgentConfig

# Test cases covering different scenarios
TEST_CASES = [
    {
        "name": "Test 1: Example.com - Click More Information",
        "start_url": "https://example.com",
        "goal": "Click the 'More information' link",
        "selector": "body",
        "max_steps": 2,
    },
    {
        "name": "Test 2: Wikipedia Main Page",
        "start_url": "https://en.wikipedia.org/wiki/Main_Page",
        "goal": "Identify the featured article title",
        "selector": "body",
        "max_steps": 1,
    },
    {
        "name": "Test 3: Google Homepage",
        "start_url": "https://www.google.com",
        "goal": "Click on the search box",
        "selector": "body",
        "max_steps": 1,
    },
    {
        "name": "Test 4: GitHub",
        "start_url": "https://github.com",
        "goal": "Click the Sign in button",
        "selector": "body",
        "max_steps": 2,
    },
    {
        "name": "Test 5: Python.org",
        "start_url": "https://www.python.org",
        "goal": "Click the Downloads link",
        "selector": "body",
        "max_steps": 2,
    },
    {
        "name": "Test 6: MDN Web Docs",
        "start_url": "https://developer.mozilla.org",
        "goal": "Click on the search or main navigation",
        "selector": "body",
        "max_steps": 1,
    },
]


def run_test_suite(provider: str = "openai", model: str = "gpt-5"):
    """Run all test cases and save comprehensive logs."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_dir = Path(f"logs/test_suite_{timestamp}")
    suite_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*100)
    print(f"🧪 VISION AGENT TEST SUITE")
    print("="*100)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🤖 Provider: {provider}")
    print(f"🧠 Model: {model}")
    print(f"📂 Logs: {suite_dir.absolute()}")
    print(f"🧪 Tests: {len(TEST_CASES)}")
    print("="*100 + "\n")
    
    results = []
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'#'*100}")
        print(f"# TEST {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"{'#'*100}\n")
        
        # Create test-specific log directory
        test_log_dir = suite_dir / f"test_{i:02d}_{test_case['name'].split(':')[0].replace(' ', '_').lower()}"
        test_log_dir.mkdir(exist_ok=True)
        
        cfg = AgentConfig(
            provider=provider,
            model=model,
            selector=test_case["selector"],
            max_steps=test_case["max_steps"],
            log_dir=str(test_log_dir),
        )
        
        agent = VisionWebAgent()
        
        try:
            result = agent.run(test_case["start_url"], test_case["goal"], cfg)
            result["test_name"] = test_case["name"]
            result["success"] = True
            results.append(result)
            print(f"\n✅ TEST {i} PASSED")
        except Exception as e:
            print(f"\n❌ TEST {i} FAILED: {e}")
            results.append({
                "test_name": test_case["name"],
                "success": False,
                "error": str(e),
            })
        
        # Small delay between tests
        import time
        time.sleep(2)
    
    # Save summary
    summary_path = suite_dir / "test_suite_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "provider": provider,
            "model": model,
            "total_tests": len(TEST_CASES),
            "results": results,
        }, f, indent=2)
    
    # Print summary
    print("\n" + "="*100)
    print("📊 TEST SUITE SUMMARY")
    print("="*100)
    
    passed = sum(1 for r in results if r.get("success", False))
    failed = len(results) - passed
    
    print(f"✅ Passed: {passed}/{len(TEST_CASES)}")
    print(f"❌ Failed: {failed}/{len(TEST_CASES)}")
    print(f"📂 Full logs: {suite_dir.absolute()}")
    print(f"📄 Summary: {summary_path.name}")
    print("="*100 + "\n")
    
    # List all screenshot files
    screenshots = sorted(suite_dir.glob("**/*.png"))
    if screenshots:
        print(f"\n📸 SCREENSHOTS SAVED ({len(screenshots)} total):")
        print("-"*100)
        for screenshot in screenshots[:20]:  # Show first 20
            rel_path = screenshot.relative_to(suite_dir)
            print(f"   {rel_path}")
        if len(screenshots) > 20:
            print(f"   ... and {len(screenshots) - 20} more")
        print("-"*100 + "\n")
    
    return results


if __name__ == "__main__":
    provider = os.getenv("VISION_PROVIDER", "openai")
    model = os.getenv("VISION_MODEL", "gpt-5")
    
    if len(sys.argv) > 1:
        provider = sys.argv[1]
    if len(sys.argv) > 2:
        model = sys.argv[2]
    
    # Clear the base URL override if present
    if "OPENAI_BASE_URL" in os.environ and os.environ["OPENAI_BASE_URL"] != "https://api.openai.com/v1":
        print(f"⚠️  Clearing environment override: OPENAI_BASE_URL={os.environ['OPENAI_BASE_URL']}")
        os.environ["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
    
    results = run_test_suite(provider, model)
    
    # Exit with appropriate code
    failed = sum(1 for r in results if not r.get("success", False))
    sys.exit(1 if failed > 0 else 0)

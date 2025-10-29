"""
Redfinger automation runner for Agent S3.
Launches browser to Redfinger URL and executes task.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

# Add Agent-S to path
sys.path.insert(0, '/workspace')

from gui_agents.s3.agents.agent_s import AgentS3
from gui_agents.s3.agents.grounding import OSWorldACI

def launch_redfinger_session(url: str, maximize: bool = True):
    """Launch browser and navigate to Redfinger session."""
    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=False,
        args=[
            '--start-fullscreen' if maximize else '--start-maximized',
            '--disable-blink-features=AutomationControlled'
        ]
    )
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto(url)
    page.wait_for_load_state('domcontentloaded')
    time.sleep(5)  # Wait for Redfinger to load

    return p, browser, page

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='Redfinger session URL')
    parser.add_argument('--task', required=True, help='Task description')
    parser.add_argument('--max-steps', type=int, default=50)
    args = parser.parse_args()

    # Launch Redfinger in browser (full-screen in container = 0,0 coordinates)
    print(f"Opening Redfinger: {args.url}")
    p, browser, page = launch_redfinger_session(args.url)

    # Build Agent S3
    print("Initializing Agent S3...")

    # Reasoner config - MUST be vision-capable model
    # Default to GPT-5 (2025) if not specified
    reasoner_provider = os.getenv("REASONER_PROVIDER", os.getenv("VISION_PROVIDER", "openai"))
    engine_params = {
        "engine_type": reasoner_provider,
        "model": os.getenv("REASONER_MODEL", "gpt-5-2025-08-07"),
        "api_key": os.getenv("ZAI_API_KEY" if reasoner_provider == "zai" else "OPENAI_API_KEY"),
    }

    # Add base_url for ZAI
    if reasoner_provider == "zai":
        engine_params["base_url"] = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")

    # Grounding config - Also MUST be vision-capable model
    # Default to GPT-5 (2025) if not specified
    vision_provider = os.getenv("VISION_PROVIDER", "openai")
    grounding_params = {
        "engine_type": vision_provider,
        "model": os.getenv("VISION_MODEL", "gpt-5-2025-08-07"),
        "api_key": os.getenv("ZAI_API_KEY" if vision_provider == "zai" else "OPENAI_API_KEY"),
        "grounding_width": 1920,
        "grounding_height": 1080,
    }

    # Add base_url for ZAI grounding
    if vision_provider == "zai":
        grounding_params["base_url"] = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4")

    grounding_agent = OSWorldACI(
        env=None,
        platform="linux",
        engine_params_for_generation=engine_params,
        engine_params_for_grounding=grounding_params,
        width=1920,
        height=1080,
    )

    agent = AgentS3(engine_params, grounding_agent)

    # Agent loop
    print(f"Starting task: {args.task}")
    import pyautogui
    import io
    import subprocess
    from PIL import Image

    for step in range(args.max_steps):
        print(f"\n--- Step {step+1}/{args.max_steps} ---")

        # Capture screen using scrot (works in container)
        screenshot_path = f'/tmp/screenshot_{step}.png'
        subprocess.run(['scrot', screenshot_path], check=True)
        screenshot = Image.open(screenshot_path)
        buf = io.BytesIO()
        screenshot.save(buf, format='PNG')
        obs = {"screenshot": buf.getvalue()}

        # Get agent decision
        info, actions = agent.predict(instruction=args.task, observation=obs)

        if not actions:
            print("Agent completed task!")
            break

        # Execute actions
        for action_code in actions:
            print(f"Executing: {action_code[:100]}...")
            exec(action_code)
            time.sleep(0.5)

    browser.close()
    p.stop()

if __name__ == "__main__":
    main()

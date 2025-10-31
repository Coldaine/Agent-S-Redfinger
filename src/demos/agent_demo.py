from __future__ import annotations

import argparse
import os
from dotenv import load_dotenv

from src.agent.web_agent import VisionWebAgent, AgentConfig


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Minimal vision web agent demo")
    parser.add_argument("--start", type=str, default="https://example.com", help="Start URL")
    parser.add_argument("--goal", type=str, required=True, help="High-level goal for the agent")
    parser.add_argument(
        "--selector", type=str, default="body", help="CSS selector for the container element"
    )
    parser.add_argument(
        "--max-steps", type=int, default=3, help="Maximum steps (observe->click) to perform"
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=os.getenv("VISION_PROVIDER", "none"),
        help="Provider id: openai | zai | none",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("VISION_MODEL", "gpt-5-vision"),
        help="Model name for the provider",
    )

    args = parser.parse_args()

    cfg = AgentConfig(
        provider=args.provider,
        model=args.model,
        selector=args.selector,
        max_steps=args.max_steps,
    )

    agent = VisionWebAgent()
    result = agent.run(args.start, args.goal, cfg)
    print("Result:", result)


if __name__ == "__main__":
    main()

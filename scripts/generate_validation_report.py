import os
import json
from datetime import datetime
from typing import Dict, Any, List

# Roots to scan for validation artifacts. Adjust as your project evolves.
RESULTS_ROOTS: List[str] = [
    "results",           # generic output folder if present
    "logs",              # logs may contain per-case subfolders
    "osworld_results",   # optional convention
    os.path.join("osworld_setup", "s2", "results"),
    os.path.join("osworld_setup", "s2_5", "results"),
    os.path.join("osworld_setup", "s3", "results"),
]

# File names that indicate artifacts of interest
ARTIFACT_FILES = (
    "result.json",
    "facts.jsonl",
    "final_screenshot.png",
    "stdout.log",
    "stderr.log",
    "trace.jsonl",
)


def _safe_json_load(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def collect_results(root_dirs: List[str]) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "domains": {},
        "scanned_roots": [],
    }

    for root in root_dirs:
        if not root:
            continue
        if not os.path.exists(root):
            continue
        report["scanned_roots"].append(root)

        # Domain = immediate subfolder name under root
        for domain in sorted(os.listdir(root)):
            domain_path = os.path.join(root, domain)
            if not os.path.isdir(domain_path):
                continue

            domain_key = f"{root}/{domain}" if root not in ("results", "logs", "osworld_results") else domain
            domain_summary = report["domains"].setdefault(
                domain_key,
                {"examples": {}, "counts": {"passed": 0, "failed": 0, "unknown": 0, "total": 0}},
            )

            for example_id in sorted(os.listdir(domain_path)):
                example_path = os.path.join(domain_path, example_id)
                if not os.path.isdir(example_path):
                    continue

                status = "unknown"
                artifacts = {}

                # Collect artifacts
                for fname in ARTIFACT_FILES:
                    fp = os.path.join(example_path, fname)
                    if os.path.exists(fp):
                        artifacts[fname] = True

                # Heuristics for status: prefer explicit result.json → {status: passed|failed}
                rj = os.path.join(example_path, "result.json")
                if os.path.exists(rj):
                    data = _safe_json_load(rj)
                    if isinstance(data, dict):
                        status = str(data.get("status", "unknown")).lower()

                domain_summary["examples"][example_id] = {
                    "status": status,
                    "artifacts": artifacts,
                }
                domain_summary["counts"]["total"] += 1
                if status == "passed":
                    domain_summary["counts"]["passed"] += 1
                elif status == "failed":
                    domain_summary["counts"]["failed"] += 1
                else:
                    domain_summary["counts"]["unknown"] += 1

    return report


def to_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Validation Status")
    lines.append("")
    lines.append(f"Generated: {report.get('generated_at', '')}")
    scanned = report.get("scanned_roots", [])
    if scanned:
        lines.append("")
        lines.append("Scanned roots: " + ", ".join(scanned))
    lines.append("")

    domains = report.get("domains", {})
    if not domains:
        lines.append("No validation artifacts found yet.")
        lines.append("")
        lines.append("Run this to regenerate:")
        lines.append("")
        lines.append("```powershell")
        lines.append("python scripts/generate_validation_report.py")
        lines.append("```")
        return "\n".join(lines)

    for domain, info in sorted(domains.items()):
        counts = info.get("counts", {})
        total = counts.get("total", 0)
        passed = counts.get("passed", 0)
        failed = counts.get("failed", 0)
        unknown = counts.get("unknown", 0)
        lines.append(f"## {domain} — {passed}/{total} passed, {failed} failed, {unknown} unknown")
        lines.append("")
        lines.append("| example_id | status | artifacts |")
        lines.append("|---|---:|---|")
        for ex, meta in sorted(info.get("examples", {}).items()):
            arts = ", ".join(sorted(meta.get("artifacts", {}).keys())) or "-"
            lines.append(f"| {ex} | {meta.get('status', 'unknown')} | {arts} |")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    report = collect_results(RESULTS_ROOTS)
    md = to_markdown(report)
    os.makedirs("docs", exist_ok=True)
    out_path = os.path.join("docs", "VALIDATION_STATUS.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

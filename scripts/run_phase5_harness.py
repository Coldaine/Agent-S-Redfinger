import argparse
import datetime
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from typing import Optional, List, Dict

# Harness for running Phase 5 integration tests with robust logging, timeouts, and results.
# Artifacts are written under logs/phase5/<timestamp>/ including stdout.log, stderr.log, meta.json, result.json.
# Designed for Windows host (PowerShell) with docker-compose.


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def attempt_start_docker_desktop() -> None:
    """Best-effort start of Docker Desktop on Windows (no-op elsewhere)."""
    if os.name != "nt":
        return
    candidates = [
        r"C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
        r"C:\\Program Files (x86)\\Docker\\Docker\\Docker Desktop.exe",
    ]
    for exe in candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass


def check_docker_ready(timeout: int = 30) -> None:
    start = time.time()
    last_err: Optional[str] = None
    while time.time() - start < timeout:
        try:
            out = subprocess.check_output(["docker", "ps"], stderr=subprocess.STDOUT, text=True)
            if out is not None:
                return
        except subprocess.CalledProcessError as e:
            last_err = e.output
        except FileNotFoundError:
            last_err = "docker CLI not found in PATH"
        time.sleep(2)
    raise RuntimeError(f"Docker engine not reachable within {timeout}s. Last error: {last_err}")


def build_compose_run_cmd(url: str, task: str, max_steps: int,
                          provider: str, model: str, model_temp: Optional[float],
                          vision_model: Optional[str] = None,
                          extra_env: Optional[Dict[str, str]] = None,
                          container_name: Optional[str] = None) -> List[str]:
    # Environment overrides for the run
    env_args: List[str] = []
    # Reasoner and vision models
    env_args += ["-e", f"REASONER_MODEL={model}"]
    env_args += ["-e", f"VISION_MODEL={vision_model or model}"]
    # Temperature override if provided
    if model_temp is not None:
        env_args += ["-e", f"MODEL_TEMPERATURE={model_temp}"]
    # Provider for vision (kept aligned)
    env_args += ["-e", f"VISION_PROVIDER={provider}"]
    # Any extra env
    if extra_env:
        for k, v in extra_env.items():
            env_args += ["-e", f"{k}={v}"]

    # Compose the docker-compose run command
    cmd = ["docker-compose", "run", "--rm"]
    if container_name:
        cmd += ["--name", container_name]
    cmd += [
        *env_args,
        "agent-redfinger", "python3", "/workspace/redfinger/run_redfinger.py",
        "--url", url,
        "--task", task,
        "--max-steps", str(max_steps),
    ]
    return cmd


def stream_output(pipe, log_file, last_line_ts_ref, stop_event):
    with open(log_file, "w", encoding="utf-8", errors="ignore") as f:
        for line in iter(pipe.readline, ""):
            f.write(line)
            f.flush()
            last_line_ts_ref[0] = time.time()
            if stop_event.is_set():
                break


def run_with_timeouts(cmd: List[str], workdir: str, overall_timeout: int, stall_timeout: int, container_name: Optional[str]) -> Dict:
    ensure_dir(workdir)
    stdout_log = os.path.join(workdir, "stdout.log")
    stderr_log = os.path.join(workdir, "stderr.log")

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    last_line_ts = [time.time()]
    stop_event = threading.Event()

    t_out = threading.Thread(target=stream_output, args=(proc.stdout, stdout_log, last_line_ts, stop_event))
    t_err = threading.Thread(target=stream_output, args=(proc.stderr, stderr_log, last_line_ts, stop_event))
    t_out.daemon = True
    t_err.daemon = True
    t_out.start()
    t_err.start()

    start = time.time()
    timed_out = False
    stalled = False
    exit_code = None

    try:
        while True:
            if proc.poll() is not None:
                exit_code = proc.returncode
                break
            if time.time() - start > overall_timeout:
                timed_out = True
                proc.kill()
                break
            if time.time() - last_line_ts[0] > stall_timeout:
                stalled = True
                proc.kill()
                break
            time.sleep(1)
    finally:
        stop_event.set()
        try:
            t_out.join(timeout=3)
            t_err.join(timeout=3)
        except Exception:
            pass

        # Best-effort cleanup if we assigned a name and the container might still be running
        if container_name and (timed_out or stalled):
            try:
                subprocess.run(["docker", "rm", "-f", container_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    return {
        "stdout_log": stdout_log,
        "stderr_log": stderr_log,
        "timed_out": timed_out,
        "stalled": stalled,
        "exit_code": exit_code,
        "duration_sec": round(time.time() - start, 2),
    }


def detect_success(stdout_path: str) -> Dict[str, bool]:
    # Heuristics: look for evidence of action execution or completion
    signals = {
        "saw_start": False,
        "saw_action": False,
        "saw_complete": False,
        "saw_error_400_temperature": False,
        "saw_harness_pass": False,
        "saw_harness_fail": False,
    }
    try:
        with open(stdout_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "Starting task:" in line:
                    signals["saw_start"] = True
                if "Executing:" in line:
                    signals["saw_action"] = True
                if "Agent completed task" in line:
                    signals["saw_complete"] = True
                if "Unsupported value: 'temperature'" in line or "param': 'temperature'" in line:
                    signals["saw_error_400_temperature"] = True
                if "HARNESS:STATUS=passed" in line:
                    signals["saw_harness_pass"] = True
                if "HARNESS:STATUS=failed" in line:
                    signals["saw_harness_fail"] = True
    except FileNotFoundError:
        pass
    return signals


def main():
    parser = argparse.ArgumentParser(description="Phase 5 harness runner with logging and timeouts")
    parser.add_argument("--url", default="https://www.google.com")
    parser.add_argument("--task", default="Click on the search box and type weather")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default="gpt-5-2025-08-07")
    parser.add_argument("--model-temperature", type=float, default=1.0)
    parser.add_argument("--vision-model", default=None)
    parser.add_argument("--overall-timeout", type=int, default=900, help="Overall timeout in seconds (default 15m)")
    parser.add_argument("--stall-timeout", type=int, default=120, help="No-output stall timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Only check Docker readiness and exit")
    parser.add_argument("--auto-start-docker", action="store_true", help="Attempt to start Docker Desktop on Windows before checking readiness")
    parser.add_argument("--compose-down-before", action="store_true", help="Run 'docker-compose down --remove-orphans' before test")
    parser.add_argument("--compose-down-after", action="store_true", help="Run 'docker-compose down --remove-orphans' after test")
    parser.add_argument("--compose-build", action="store_true", help="Run 'docker-compose build' before test")
    parser.add_argument("--container-name", default=None, help="Assign a name to the test container for easier cleanup")

    args = parser.parse_args()

    # Preflight
    if args.auto_start_docker:
        attempt_start_docker_desktop()
    check_docker_ready()
    if args.dry_run:
        print("Docker is reachable. Dry-run OK.")
        return 0

    # Run directory
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join("logs", "phase5", ts)
    ensure_dir(run_dir)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    default_container_name = f"agent-s3-phase5-{ts}" if args.container_name is None else args.container_name

    meta = {
        "started_at": _now_iso(),
        "provider": args.provider,
        "model": args.model,
        "model_temperature": args.model_temperature,
        "vision_model": args.vision_model or args.model,
        "url": args.url,
        "task": args.task,
        "max_steps": args.max_steps,
        "overall_timeout": args.overall_timeout,
        "stall_timeout": args.stall_timeout,
        "container_name": default_container_name,
        "compose_down_before": bool(args.compose_down_before),
        "compose_down_after": bool(args.compose_down_after),
        "compose_build": bool(args.compose_build),
        "cmd": None,
    }

    # Optional compose hygiene
    if args.compose_down_before:
        try:
            subprocess.run(["docker-compose", "down", "--remove-orphans"], check=False)
        except Exception:
            pass
    if args.compose_build:
        try:
            subprocess.run(["docker-compose", "build"], check=True)
        except Exception as e:
            print(f"Build failed: {e}")
            # Continue to allow using existing image

    cmd = build_compose_run_cmd(
        url=args.url,
        task=args.task,
        max_steps=args.max_steps,
        provider=args.provider,
        model=args.model,
        model_temp=args.model_temperature,
        vision_model=args.vision_model,
        container_name=default_container_name,
    )
    meta["cmd"] = cmd

    with open(os.path.join(run_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    outcome = run_with_timeouts(
        cmd,
        workdir=run_dir,
        overall_timeout=args.overall_timeout,
        stall_timeout=args.stall_timeout,
        container_name=default_container_name,
    )

    signals = detect_success(outcome["stdout_log"])

    status = "unknown"
    # Primary: explicit status marker from inner runner
    if signals.get("saw_harness_pass"):
        status = "passed"
    elif signals.get("saw_harness_fail"):
        status = "failed"
    else:
        # Fallback heuristics
        if signals.get("saw_complete") or signals.get("saw_action"):
            status = "passed"
        if outcome["timed_out"] or outcome["stalled"]:
            status = "failed"
        if signals.get("saw_error_400_temperature"):
            status = "failed"

    result = {
        "status": status,
        "ended_at": _now_iso(),
        **meta,
        **outcome,
        "signals": signals,
    }

    with open(os.path.join(run_dir, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Run complete. Status: {status}. Artifacts: {run_dir}")

    # Optional compose cleanup
    if args.compose_down_after:
        try:
            subprocess.run(["docker-compose", "down", "--remove-orphans"], check=False)
        except Exception:
            pass

    # Optionally regenerate validation status
    try:
        subprocess.run([sys.executable, os.path.join("scripts", "generate_validation_report.py")], check=False)
    except Exception:
        pass

    return 0 if status == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())

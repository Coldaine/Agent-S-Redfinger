import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from typing import Optional, List, Dict, Set

# Harness for running Phase 5 integration tests with robust logging, timeouts, and results.
# Refactored for real-time monitoring with fast feedback loops.
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


class LogMonitor:
    """Real-time log monitor with fast signal detection."""
    
    def __init__(self, log_file: str, monitor_interval: float = 2.0):
        self.log_file = log_file
        self.monitor_interval = monitor_interval
        self.signals = {
            "saw_start": False,
            "saw_action": False,
            "saw_complete": False,
            "saw_error": False,
            "saw_error_400_temperature": False,
            "saw_harness_pass": False,
            "saw_harness_fail": False,
            "saw_api_error": False,
            "saw_import_error": False,
        }
        self.step_count = 0
        self.last_activity = time.time()
        
    def check_line(self, line: str) -> bool:
        """Check a line for signals. Returns True if terminal signal detected."""
        self.last_activity = time.time()
        
        # Success signals
        if "Starting task:" in line:
            self.signals["saw_start"] = True
            print(f"  ✓ Task started")
        if "Executing:" in line or "Action:" in line:
            self.signals["saw_action"] = True
            self.step_count += 1
            print(f"  ✓ Action {self.step_count} executed")
        if "Agent completed task" in line:
            self.signals["saw_complete"] = True
            print(f"  ✓ Task completed!")
            return True
        if "HARNESS:STATUS=passed" in line:
            self.signals["saw_harness_pass"] = True
            print(f"  ✓ HARNESS PASSED")
            return True
            
        # Failure signals
        if "HARNESS:STATUS=failed" in line:
            self.signals["saw_harness_fail"] = True
            print(f"  ✗ HARNESS FAILED")
            return True
        if "Unsupported value: 'temperature'" in line or "param': 'temperature'" in line:
            self.signals["saw_error_400_temperature"] = True
            print(f"  ✗ Temperature parameter error detected")
            return True
        if "API key" in line.lower() and ("invalid" in line.lower() or "error" in line.lower()):
            self.signals["saw_api_error"] = True
            print(f"  ✗ API authentication error")
            return True
        if "ImportError" in line or "ModuleNotFoundError" in line:
            self.signals["saw_import_error"] = True
            print(f"  ✗ Import error detected")
            return True
        if "Error:" in line or "ERROR:" in line or "Exception:" in line:
            self.signals["saw_error"] = True
            # Don't return True - not all errors are terminal
            
        return False
    
    def read_log_tail(self, lines: int = 50) -> List[str]:
        """Read last N lines from log file."""
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                return f.readlines()[-lines:]
        except FileNotFoundError:
            return []
    
    def get_status(self) -> str:
        """Determine current status from signals."""
        if self.signals["saw_harness_pass"]:
            return "passed"
        if self.signals["saw_harness_fail"]:
            return "failed"
        if self.signals["saw_error_400_temperature"]:
            return "failed"
        if self.signals["saw_api_error"]:
            return "failed"
        if self.signals["saw_import_error"]:
            return "failed"
        if self.signals["saw_complete"]:
            return "passed"
        if self.signals["saw_action"]:
            return "running"
        if self.signals["saw_start"]:
            return "started"
        return "unknown"


def run_with_monitoring(cmd: List[str], workdir: str, overall_timeout: int, 
                       stall_timeout: int, monitor_interval: float,
                       container_name: Optional[str]) -> Dict:
    """Run container and actively monitor logs with fast feedback."""
    ensure_dir(workdir)
    stdout_log = os.path.join(workdir, "stdout.log")
    stderr_log = os.path.join(workdir, "stderr.log")
    
    # Start the container
    print(f"Starting container: {container_name}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Start log file writers
    stdout_f = open(stdout_log, "w", encoding="utf-8", errors="ignore")
    stderr_f = open(stderr_log, "w", encoding="utf-8", errors="ignore")
    
    monitor = LogMonitor(stdout_log, monitor_interval)
    start = time.time()
    timed_out = False
    stalled = False
    exit_code = None
    last_log_pos = 0
    
    print(f"\nMonitoring logs (checking every {monitor_interval}s)...")
    print("=" * 60)
    
    try:
        while True:
            # Check if process finished
            poll_result = proc.poll()
            if poll_result is not None:
                exit_code = poll_result
                print(f"\n✓ Container exited with code {exit_code}")
                break
            
            # Read and write any new output
            for pipe, log_f in [(proc.stdout, stdout_f), (proc.stderr, stderr_f)]:
                if pipe is None:
                    continue
                try:
                    while True:
                        line = pipe.readline()
                        if not line:
                            break
                        log_f.write(line)
                        log_f.flush()
                        
                        # Check for signals in stdout
                        if pipe == proc.stdout:
                            is_terminal = monitor.check_line(line)
                            if is_terminal:
                                print(f"\n✓ Terminal signal detected, stopping container...")
                                proc.terminate()
                                time.sleep(2)
                                if proc.poll() is None:
                                    proc.kill()
                                exit_code = 0
                                break
                except:
                    pass
            
            # Check timeouts
            elapsed = time.time() - start
            if elapsed > overall_timeout:
                timed_out = True
                print(f"\n✗ Overall timeout ({overall_timeout}s) reached")
                proc.kill()
                break
            
            stall_time = time.time() - monitor.last_activity
            if stall_time > stall_timeout:
                stalled = True
                print(f"\n✗ Stall timeout ({stall_timeout}s) - no activity")
                proc.kill()
                break
            
            # Status update
            status = monitor.get_status()
            print(f"[{elapsed:.0f}s] Status: {status}, Steps: {monitor.step_count}, Last activity: {stall_time:.0f}s ago", end='\r')
            
            time.sleep(monitor_interval)
            
    finally:
        stdout_f.close()
        stderr_f.close()
        
        # Cleanup container if needed
        if container_name and (timed_out or stalled):
            print(f"\nCleaning up container: {container_name}")
            try:
                subprocess.run(["docker", "rm", "-f", container_name], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
    
    print("\n" + "=" * 60)
    
    return {
        "stdout_log": stdout_log,
        "stderr_log": stderr_log,
        "timed_out": timed_out,
        "stalled": stalled,
        "exit_code": exit_code,
        "duration_sec": round(time.time() - start, 2),
        "step_count": monitor.step_count,
        "signals": monitor.signals,
    }


def detect_success_fallback(stdout_path: str) -> Dict[str, bool]:
    """Fallback signal detection for post-mortem analysis."""
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
    parser.add_argument("--monitor-interval", type=float, default=2.0, help="How often to check logs (seconds, default 2.0)")
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

    outcome = run_with_monitoring(
        cmd,
        workdir=run_dir,
        overall_timeout=args.overall_timeout,
        stall_timeout=args.stall_timeout,
        monitor_interval=args.monitor_interval,
        container_name=default_container_name,
    )

    # Signals are already in outcome from monitor
    signals = outcome.get("signals", {})

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

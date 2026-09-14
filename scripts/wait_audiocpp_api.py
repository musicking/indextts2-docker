"""Bounded API readiness check, including container-exit diagnostics."""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request


def wait_for_api(url, timeout=120, interval=1, container=None):
    deadline = time.monotonic() + timeout
    last_error = "not attempted"
    while time.monotonic() < deadline:
        if container:
            state = json.loads(subprocess.check_output([
                "docker", "inspect", "--format", "{{json .State}}", container
            ], text=True))
            if not state.get("Running"):
                raise RuntimeError(f"API container stopped: {json.dumps(state)}")
        try:
            remaining = max(0.01, deadline - time.monotonic())
            with urllib.request.urlopen(url, timeout=min(3, remaining)) as response:
                if response.status == 200:
                    response.read()
                    return
                last_error = f"HTTP {response.status}"
        except (OSError, urllib.error.URLError) as error:
            last_error = str(error)
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise TimeoutError(f"API not ready after {timeout}s: {last_error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:7864/health")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--container")
    args = parser.parse_args()
    wait_for_api(args.url, timeout=args.timeout, container=args.container)
    print("API readiness: OK")

"""Set up and run the case study with Python's standard library only."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def run_command(command: list[str], env: dict[str, str]) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def fingerprint(*paths: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def install_if_changed(
    command: list[str],
    stamp: Path,
    digest: str,
    env: dict[str, str],
    reinstall: bool,
) -> None:
    if not reinstall and stamp.is_file() and stamp.read_text() == digest:
        return
    run_command(command, env)
    stamp.write_text(digest)


def check_prerequisites() -> str:
    if sys.version_info < (3, 12):
        raise RuntimeError("Python 3.12 or newer is required. Run this script with that interpreter.")
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        raise RuntimeError("Node.js 22.12+ and npm must be installed and available on PATH.")
    version = subprocess.check_output([node, "--version"], text=True).strip()
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (22, 12, 0):
        raise RuntimeError(f"Node.js 22.12+ is required; found {version}.")
    return npm


def check_port(port: int, name: str, option: str) -> None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.bind(("127.0.0.1", port))
    except OSError as exc:
        raise RuntimeError(
            f"Cannot use {name} port {port}: {exc}. Stop the existing server or "
            f"choose another port with {option}."
        ) from exc


def prepare(npm: str, env: dict[str, str], reinstall: bool) -> None:
    if not PYTHON.is_file():
        print("Creating .venv…", flush=True)
        run_command([sys.executable, "-m", "venv", str(VENV)], env)
        reinstall = True
    version = subprocess.check_output(
        [str(PYTHON), "-c", "import sys; print(sys.version_info.major, sys.version_info.minor)"],
        text=True,
    )
    if tuple(map(int, version.split())) < (3, 12):
        raise RuntimeError("The existing .venv uses Python older than 3.12. Recreate it with Python 3.12+.")

    print("Checking Python dependencies…", flush=True)
    requirements = ROOT / "backend" / "requirements.txt"
    install_if_changed(
        [str(PYTHON), "-m", "pip", "install", "-r", str(requirements)],
        VENV / ".launcher-requirements.sha256", fingerprint(requirements), env, reinstall,
    )
    print("Checking frontend dependencies…", flush=True)
    frontend = ROOT / "frontend"
    install_if_changed(
        [npm, "ci", "--prefix", str(frontend), "--no-audit", "--no-fund"],
        frontend / "node_modules" / ".launcher-package-lock.sha256",
        fingerprint(frontend / "package.json", frontend / "package-lock.json"), env, reinstall,
    )
    print("Preparing SQLite…", flush=True)
    run_command([str(PYTHON), "-m", "backend.app.initialize"], env)


def start(command: list[str], env: dict[str, str]) -> subprocess.Popen:
    options = {"start_new_session": True} if os.name != "nt" else {
        "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP,
    }
    return subprocess.Popen(command, cwd=ROOT, env=env, **options)


def stop(process: subprocess.Popen) -> None:
    # Stop the whole group: Uvicorn --reload and npm both spawn child processes.
    try:
        if os.name == "nt":
            if process.poll() is None:
                process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], check=False)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait()


def wait_for_server(process: subprocess.Popen, url: str) -> None:
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Server exited before {url} was ready. See its output above.")
        try:
            with opener.open(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError):
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}. See server output above.")


def port_number(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("Port must be between 1 and 65535.")
    return port


def interrupt(_signum, _frame) -> None:
    raise KeyboardInterrupt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=port_number, default=8000)
    parser.add_argument("--web-port", type=port_number, default=5173)
    parser.add_argument("--reinstall", action="store_true", help="Reinstall dependencies even if unchanged")
    args = parser.parse_args()
    if args.api_port == args.web_port:
        parser.error("The API and frontend need different ports.")
    signal.signal(signal.SIGTERM, interrupt)
    processes: list[tuple[str, subprocess.Popen]] = []
    env = {**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    try:
        npm = check_prerequisites()
        check_port(args.api_port, "API", "--api-port")
        check_port(args.web_port, "frontend", "--web-port")
        prepare(npm, env, args.reinstall)
        api = start([
            str(PYTHON), "-m", "uvicorn", "backend.app.main:app", "--reload",
            "--host", "127.0.0.1", "--port", str(args.api_port),
        ], env)
        processes.append(("API", api))
        api_url = f"http://127.0.0.1:{args.api_port}"
        wait_for_server(api, f"{api_url}/api/listings")

        web = start([
            npm, "run", "dev", "--prefix", str(ROOT / "frontend"), "--",
            "--host", "127.0.0.1", "--port", str(args.web_port), "--strictPort",
        ], {**env, "API_PROXY_TARGET": api_url})
        processes.append(("Frontend", web))
        web_url = f"http://127.0.0.1:{args.web_port}"
        wait_for_server(web, web_url)
        wait_for_server(web, f"{web_url}/api/listings")
        print(f"\nReady: {web_url}\nAPI docs: {api_url}/docs\nPress Control+C to stop both servers.\n", flush=True)
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    raise RuntimeError(f"{name} exited unexpectedly (code {process.returncode}).")
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nStopping servers…", flush=True)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"\nError: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        for _, process in reversed(processes):
            stop(process)


if __name__ == "__main__":
    sys.exit(main())

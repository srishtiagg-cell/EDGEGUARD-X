"""Start EDGEGUARD-X for this PC and other devices on the same Wi-Fi."""

from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser


PORT = 8505
ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / ".venv"
PYTHON = APP_DIR / "Scripts" / "python.exe"
APP_FILE = APP_DIR / "app2.py"


def get_lan_ip() -> str | None:
    """Get the IPv4 address used by the default route without sending data."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 80))
        address = probe.getsockname()[0]
        return address if not address.startswith("127.") else None
    except OSError:
        return None
    finally:
        probe.close()


def responds(url: str) -> bool:
    try:
        with urlopen(url, timeout=2) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def main() -> int:
    if not PYTHON.is_file():
        print(f"Project Python environment not found: {PYTHON}")
        input("Press Enter to close.")
        return 1

    lan_ip = get_lan_ip()
    if not lan_ip:
        print("Could not detect a Wi-Fi/LAN IPv4 address. The dashboard will open on this PC only.")
        lan_ip = "127.0.0.1"

    lan_url = f"http://{lan_ip}:{PORT}"
    local_url = f"http://127.0.0.1:{PORT}"

    if responds(lan_url):
        print("EDGEGUARD-X is already running on this network.")
    elif responds(local_url):
        print("A localhost-only dashboard is already using port 8505.")
        print("Close its Streamlit window, then run this launcher again for phone access.")
        input("Press Enter to close.")
        return 1
    else:
        environment = os.environ.copy()
        environment["OPENBLAS_NUM_THREADS"] = "1"
        environment["OMP_NUM_THREADS"] = "1"
        environment["MKL_NUM_THREADS"] = "1"
        command = [
            str(PYTHON), "-m", "streamlit", "run", str(APP_FILE),
            "--server.address", lan_ip,
            "--server.port", str(PORT),
            "--server.headless", "true",
            "--server.fileWatcherType", "none",
        ]
        creation_flags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
        subprocess.Popen(command, cwd=APP_DIR, env=environment, creationflags=creation_flags)

        for _ in range(45):
            if responds(lan_url):
                break
            time.sleep(1)
        else:
            if responds(local_url):
                print("Dashboard started locally, but the Wi-Fi link did not respond.")
                print("Windows Firewall may need to allow Python on private networks.")
                lan_url = local_url
            else:
                print("Dashboard did not respond. Check the Streamlit window for startup errors.")
                input("Press Enter to close.")
                return 1

    print(f"Dashboard link: {lan_url}")
    print("For a phone/tablet, join the same Wi-Fi as this computer.")
    webbrowser.open(lan_url)
    input("Press Enter to close this launcher. The dashboard server window stays open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Windows GUI smoke test for the packaged Tkinter application.

Captures the real executable in the GitHub Actions Windows desktop session.
Screenshots are uploaded as an artifact so layout regressions can be reviewed.
"""
import subprocess
import time
from pathlib import Path

import pyautogui
import pygetwindow


APP_TITLE = "Database Yedekle"
EXE = Path("dist") / "Database Yedekle.exe"
OUT = Path("gui-test-output")
OUT.mkdir(exist_ok=True)


def find_window(timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        matches = [
            w for w in pygetwindow.getWindowsWithTitle(APP_TITLE)
            if w.width >= 700 and w.height >= 500
        ]
        if matches:
            return matches[0]
        time.sleep(1)
    raise AssertionError(f"Application window '{APP_TITLE}' did not appear")


def capture(window, filename):
    window.activate()
    time.sleep(1)
    # Capture the app window itself, excluding unrelated desktop content.
    image = pyautogui.screenshot(
        region=(window.left, window.top, window.width, window.height)
    )
    path = OUT / filename
    image.save(path)
    if image.width < 700 or image.height < 500:
        raise AssertionError(f"Unexpected screenshot size: {image.size}")
    print(f"Captured {path} ({image.width}x{image.height})")


def main():
    if not EXE.exists():
        raise FileNotFoundError(f"Built executable not found: {EXE}")

    process = subprocess.Popen([str(EXE)], cwd=str(Path.cwd()))
    try:
        window = find_window()
        window.activate()
        time.sleep(3)
        capture(window, "01-main-window.png")

        # The notebook tabs are arranged left-to-right in the main window.
        # Click each tab and capture its resulting visible layout.
        for index, name in enumerate(("databases", "schedule", "storage")):
            x = window.left + (105 if index == 0 else 265 if index == 1 else 465)
            y = window.top + 105
            pyautogui.click(x, y)
            time.sleep(0.7)
            capture(window, f"02-tab-{name}.png")

        # Exercise the demo/customer-registration dialog from the header.
        pyautogui.click(
            window.left + int(window.width * 0.78),
            window.top + 65,
        )
        time.sleep(1.2)
        dialogs = [
            w for w in pygetwindow.getWindowsWithTitle("Demo erişimi")
            if w.visible
        ]
        if dialogs:
            capture(dialogs[0], "03-demo-registration.png")
        else:
            print(
                "Demo dialog not detected; main-window and tab screenshots "
                "were captured."
            )
        print("GUI smoke test completed.")
    finally:
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            process.kill()


if __name__ == "__main__":
    main()

"""Qt GUI smoke test: launch the built EXE and capture all main navigation pages."""
import subprocess,time
from pathlib import Path
import pyautogui,pygetwindow
EXE=Path("dist")/"Database Yedekle.exe"
OUT=Path("gui-test-output");OUT.mkdir(exist_ok=True)
def main():
    if not EXE.exists():raise FileNotFoundError(EXE)
    p=subprocess.Popen([str(EXE)])
    try:
        end=time.time()+60;w=None
        while time.time()<end:
            ws=[x for x in pygetwindow.getWindowsWithTitle("Database Yedekle") if x.width>=850 and x.height>=550]
            if ws:w=ws[0];break
            time.sleep(1)
        if not w:raise AssertionError("Qt main window did not appear")
        for i,name in enumerate(["main","schedule","storage"]):
            w.activate();time.sleep(.8)
            if i:
                pyautogui.click(w.left+90,w.top+190+i*45);time.sleep(.6)
            im=pyautogui.screenshot(region=(w.left,w.top,w.width,w.height));im.save(OUT/f"{i+1:02d}-{name}.png")
            print(f"Captured {name}: {im.width}x{im.height}")
    finally:
        try:p.terminate();p.wait(timeout=5)
        except Exception:p.kill()
if __name__=="__main__":main()

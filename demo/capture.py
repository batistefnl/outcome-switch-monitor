# captures d'écran + vidéo de la démo (playwright, ffmpeg pour le mp4/gif)
#   .venv/bin/python demo/capture.py
#   OPENROUTER_API_KEY=... .venv/bin/python demo/capture.py --live NCT01070316
# la partie "check a new trial" n'est filmée qu'avec une vraie clé, pas de faux résultat dans les captures
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
MEDIA = ROOT / "demo" / "media"
TRIAL = "NCT03504423"  # bon exemple : critère rétrogradé + nouveau critère principal


def start_server(port, cache):
    env = {**os.environ, "DEMO_CACHE": str(cache)}
    proc = subprocess.Popen([sys.executable, str(ROOT / "demo" / "server.py"), "--port", str(port)], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            requests.get(f"http://127.0.0.1:{port}/api/status", timeout=1)
            return proc
        except requests.RequestException:
            time.sleep(0.2)
    proc.kill()
    sys.exit("le serveur de démo n'a pas démarré")


def shot(page, name, full=False, top=True):
    if top:
        page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(300)
    page.screenshot(path=str(MEDIA / f"{name}.png"), full_page=full)
    print(f"demo/media/{name}.png")


def screenshots(browser, base, live):
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 1280, "height": 860}, color_scheme=scheme, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(f"{base}/#{TRIAL}")
        page.locator(".trial-head").wait_for()
        shot(page, f"explore-{scheme}")
        if scheme == "light":
            page.click("text=Load version history")
            page.locator(".hist .ver").first.wait_for(timeout=60000)
            page.locator(".hist").scroll_into_view_if_needed()
            shot(page, "history", top=False)
            page.goto(base)
            page.fill("#q", "influenza vaccine")
            page.locator("#results li").first.wait_for()
            shot(page, "search")
        page.click("nav >> text=Dashboard")
        page.locator("#dash svg").first.wait_for()
        shot(page, f"dashboard-{scheme}", full=True)
        if scheme == "light":
            page.locator("#dash g.bar").first.hover()
            shot(page, "dashboard-tooltip", top=False)
            page.click("nav >> text=Method & limits")
            shot(page, "method")
            if live:
                page.click("nav >> text=Check a new trial")
                page.fill("#live-id", live)
                page.click("#live-go")
                page.locator("#live-view .trial-head").wait_for(timeout=180000)
                shot(page, "live-result")
        ctx.close()
    ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=3, is_mobile=True, has_touch=True)
    page = ctx.new_page()
    page.goto(f"{base}/#{TRIAL}")
    page.locator(".trial-head").wait_for()
    shot(page, "mobile-explore")
    page.click("nav >> text=Dashboard")
    page.locator("#dash svg").first.wait_for()
    shot(page, "mobile-dashboard")
    ctx.close()


def walkthrough(browser, base, live):
    tmp = Path(tempfile.mkdtemp())
    ctx = browser.new_context(viewport={"width": 1280, "height": 760}, record_video_dir=str(tmp),
                              record_video_size={"width": 1280, "height": 760})
    page = ctx.new_page()
    pause = page.wait_for_timeout
    page.goto(base)
    pause(1500)
    page.click("#q")
    page.type("#q", "pancreas CPI-613", delay=90)
    pause(1200)
    page.locator("#results li button").first.click()
    page.locator(".trial-head").wait_for()
    pause(3000)
    page.mouse.wheel(0, 420)
    pause(2500)
    page.click("text=Load version history")
    page.locator(".hist .ver").first.wait_for(timeout=60000)
    page.locator(".hist").scroll_into_view_if_needed()
    pause(3000)
    page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
    pause(800)
    page.click("nav >> text=Dashboard")
    page.locator("#dash svg").first.wait_for()
    pause(2500)
    for i in range(4):
        page.locator("#dash g.bar").nth(i).hover()
        pause(900)
    page.mouse.wheel(0, 700)
    pause(2500)
    page.mouse.wheel(0, 700)
    pause(2500)
    if live:
        page.evaluate("window.scrollTo(0, 0)")
        page.click("nav >> text=Check a new trial")
        pause(800)
        page.type("#live-id", live, delay=90)
        page.click("#live-go")
        page.locator("#live-view .trial-head").wait_for(timeout=180000)
        pause(4000)
    page.evaluate("window.scrollTo(0, 0)")
    page.click("nav >> text=Method & limits")
    pause(3000)
    video = page.video.path()
    ctx.close()
    webm = MEDIA / "walkthrough.webm"
    shutil.move(video, webm)
    ff = shutil.which("ffmpeg")
    if not ff:
        print("ffmpeg absent : vidéo laissée en .webm")
        return
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm), "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "22", "-map_metadata", "-1", "-fflags", "+bitexact", "-flags", "+bitexact",
                    "-movflags", "+faststart", str(MEDIA / "walkthrough.mp4")], check=True)
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(webm), "-vf",
                    "fps=10,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer",
                    str(MEDIA / "walkthrough.gif")], check=True)
    webm.unlink()
    print("demo/media/walkthrough.mp4, demo/media/walkthrough.gif")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", metavar="NCT", help="filmer aussi un classement en direct (vraie clé OPENROUTER_API_KEY)")
    ap.add_argument("--port", type=int, default=8790)
    args = ap.parse_args()
    if args.live and not os.environ.get("OPENROUTER_API_KEY"):
        sys.exit("--live demande une vraie clé OPENROUTER_API_KEY.")
    MEDIA.mkdir(parents=True, exist_ok=True)
    proc = start_server(args.port, Path(tempfile.mkdtemp()) / "live.jsonl")
    base = f"http://127.0.0.1:{args.port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            screenshots(browser, base, args.live)
            walkthrough(browser, base, args.live)
            browser.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()

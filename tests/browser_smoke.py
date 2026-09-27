"""Optional local Chrome smoke test against an already-running app on port 8501.

Uses Chrome DevTools and the development dependencies. Set CHROME_PATH if a
Chromium-based browser is not on PATH. No API key is needed.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import time
from urllib.request import urlopen

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
chrome = os.getenv("CHROME_PATH") or next((path for name in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge")
                                        if (path := shutil.which(name))), None)
if not chrome:
    raise SystemExit("Set CHROME_PATH to a Chromium-based browser executable.")


def wait_for(check, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (OSError, ValueError):
            pass
        time.sleep(.25)
    raise AssertionError("Browser condition timed out")


with tempfile.TemporaryDirectory(prefix="qa-browser-") as temporary:
    process = subprocess.Popen([chrome, "--headless=new", "--disable-gpu", "--no-first-run",
                                "--remote-debugging-port=9223", "--remote-allow-origins=*",
                                f"--user-data-dir={temporary}", "--window-size=1440,1100",
                                "http://127.0.0.1:8501"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        tabs = wait_for(lambda: json.load(urlopen("http://127.0.0.1:9223/json", timeout=2)))
        page = next(tab for tab in tabs if tab["type"] == "page")
        with connect(page["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
            sequence = 0

            def command(method, params=None):
                global sequence
                sequence += 1
                ws.send(json.dumps({"id": sequence, "method": method, "params": params or {}}))
                while True:
                    result = json.loads(ws.recv(timeout=40))
                    if result.get("id") == sequence:
                        if "error" in result:
                            raise AssertionError(result["error"])
                        return result.get("result", {})

            def evaluate(expression):
                return command("Runtime.evaluate", {"expression": expression, "returnByValue": True})["result"].get("value")

            wait_for(lambda: evaluate("!!document.querySelector('input[type=file]')"))
            assert evaluate("document.querySelector('input[type=password]').value.length === 0"), "Start the app without an API key"
            def upload(path):
                document = command("DOM.getDocument")
                node = command("DOM.querySelector", {"nodeId": document["root"]["nodeId"], "selector": "input[type=file]"})
                command("DOM.setFileInputFiles", {"nodeId": node["nodeId"], "files": [str(path)]})

            upload(ROOT / "examples/messy_sample.csv")
            wait_for(lambda: evaluate("document.body.innerText.includes('500') && document.body.innerText.includes('Quality Score')"))
            assert evaluate("['Critical Issues','High Issues','Medium Issues','Low Issues'].every(t => document.body.innerText.includes(t))")
            assert evaluate("document.body.innerText.includes('LLM explanation unavailable')")
            assert evaluate("Array.from(document.querySelectorAll('button')).some(b => b.innerText.includes('Generate AI explanations') && b.disabled)"), "Remove provider credentials from the app environment/secrets for this no-key smoke test"
            wait_for(lambda: evaluate("!!document.querySelector('.js-plotly-plot')"))
            command("Browser.setDownloadBehavior", {"behavior": "allow", "downloadPath": temporary})
            assert evaluate("Array.from(document.querySelectorAll('button')).some(b => {if(b.innerText.includes('Download Markdown report')) {b.click(); return true;} return false;})")
            report = wait_for(lambda: next(Path(temporary).glob("*.md"), None))
            content = report.read_text(encoding="utf-8")
            assert "Suggested fix" in content and "500" in content and "LLM explanation unavailable" in content
            screenshot = command("Page.captureScreenshot", {"format": "png"})
            screenshot_path = ROOT / "docs/demo.png"
            screenshot_path.parent.mkdir(exist_ok=True)
            screenshot_path.write_bytes(base64.b64decode(screenshot["data"]))
            clean = Path(temporary) / "clean.csv"
            clean.write_text("signal\n" + "\n".join(str(.01 + n * .02) for n in range(100)), encoding="utf-8")
            upload(clean)
            wait_for(lambda: evaluate("document.body.innerText.includes('No findings under the implemented rules')"))
            malformed = Path(temporary) / "malformed.csv"
            malformed.write_text('a,b\n"unterminated', encoding="utf-8")
            upload(malformed)
            wait_for(lambda: evaluate("document.body.innerText.includes('Could not parse CSV')"))
            assert not evaluate("document.body.innerText.includes('Traceback')")
            assert not evaluate("Array.from(document.querySelectorAll('button')).some(b => b.innerText.includes('Download Markdown report'))")
            print("PASS: problematic and clean CSV uploads, malformed-input recovery, offline results, Plotly chart, Markdown download, screenshot")
    finally:
        process.terminate()
        process.wait(timeout=15)
        time.sleep(1)

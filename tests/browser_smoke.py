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
import socket
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
    with socket.socket() as port_probe:
        port_probe.bind(('127.0.0.1', 0))
        debug_port = port_probe.getsockname()[1]
    app_url = "http://127.0.0.1:" + os.getenv("QA_BROWSER_PORT", "8501")
    process = subprocess.Popen([chrome, "--headless=new", "--disable-gpu", "--no-first-run",
                                f"--remote-debugging-port={debug_port}", "--remote-allow-origins=*",
                                f"--user-data-dir={temporary}", "--window-size=1440,1100",
                                app_url], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    try:
        page = wait_for(lambda: next((tab for tab in json.load(urlopen(f"http://127.0.0.1:{debug_port}/json", timeout=2))
                                     if tab['type'] == 'page' and tab['url'].rstrip('/') == app_url), None))
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

            try:
                wait_for(lambda: evaluate("!!document.querySelector('input[type=file]')"))
            except AssertionError:
                print('Browser startup diagnostic:', evaluate("JSON.stringify({url: location.href, title: document.title, state: document.readyState})"))
                raise
            assert evaluate("document.querySelector('input[type=password]').value.length === 0"), "Start the app without an API key"
            def upload(path, index=0):
                document = command("DOM.getDocument")
                nodes = command("DOM.querySelectorAll", {"nodeId": document["root"]["nodeId"], "selector": "input[type=file]"})
                command("DOM.setFileInputFiles", {"nodeId": nodes["nodeIds"][index], "files": [str(path)]})

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
            assert evaluate("Array.from(document.querySelectorAll('label')).some(e => {if(e.innerText.trim() === 'Compare Against Baseline') {e.click(); return true;} return false;})")
            wait_for(lambda: evaluate("document.querySelectorAll('input[type=file]').length === 2"))
            shifted = Path(temporary) / 'current.csv'
            shifted.write_text('signal\n' + '\n'.join(str(50.01 + n * .02) for n in range(100)), encoding='utf-8')
            upload(clean, 0)
            upload(shifted, 1)
            wait_for(lambda: evaluate("Array.from(document.querySelectorAll('button')).some(b => b.innerText === 'Compare' && !b.disabled)"))
            evaluate("Array.from(document.querySelectorAll('button')).find(b => b.innerText === 'Compare').click()")
            wait_for(lambda: evaluate("document.body.innerText.includes('High observed drift')"))
            assert evaluate("document.body.innerText.includes('Baseline: clean.csv') && document.body.innerText.includes('Current: current.csv')")
            assert evaluate("Array.from(document.querySelectorAll('button')).some(b => b.innerText.includes('Explain comparison with AI') && b.disabled)")
            evaluate("Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Download comparison report')).click()")
            comparison_download = wait_for(lambda: next(Path(temporary).glob('comparison_report*.md'), None))
            assert 'numeric' in comparison_download.read_text(encoding='utf-8')
            capture = command('Page.captureScreenshot', {'format': 'png'})
            (ROOT / 'docs/comparison.png').write_bytes(base64.b64decode(capture['data']))
            upload(malformed, 1)
            wait_for(lambda: evaluate("!Array.from(document.querySelectorAll('button')).some(b => b.innerText.includes('Download comparison report'))"))
            evaluate("Array.from(document.querySelectorAll('button')).find(b => b.innerText === 'Compare').click()")
            wait_for(lambda: evaluate("document.body.innerText.includes('Could not parse CSV')"))
            assert not evaluate("document.body.innerText.includes('Traceback')")
            assert evaluate("Array.from(document.querySelectorAll('label')).some(e => {if(e.innerText.trim() === 'Investigate Dataset') {e.click(); return true;} return false;})")
            wait_for(lambda: evaluate("document.body.innerText.includes('Investigation requires a configured model/API key')"))
            upload(clean)
            assert evaluate("Array.from(document.querySelectorAll('button')).some(b => b.innerText === 'Run investigation' && b.disabled)")
            assert evaluate("document.querySelector('textarea').value.includes('2024')")
            assert not evaluate("document.body.innerText.includes('Traceback')")
            capture = command('Page.captureScreenshot', {'format': 'png'})
            (ROOT / 'docs/investigation.png').write_bytes(base64.b64decode(capture['data']))
            print("PASS: V1 uploads/recovery/chart/export; V2 comparison/recovery/export; V2.1 investigation upload, question, consent display and no-key disabled state; screenshots")
    finally:
        process.terminate()
        process.wait(timeout=15)
        time.sleep(1)

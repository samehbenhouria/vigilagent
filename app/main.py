"""VigilAgent web endpoint — the same FastAPI app runs locally, in a
container, and on AWS Lambda (ARM64) behind API Gateway.

Routes:
  GET  /              demo page (upload form + bundled example scenes)
  POST /inspect       multipart image upload -> verdict JSON + trace
  GET  /inspect/example/{name}  run one bundled example scene
  GET  /health        liveness
"""
import base64
import sys
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.orchestrator import VigilAgent, annotate

REF = cv2.imread(str(ROOT / "data" / "scenes" / "clean.png"))
AGENT = VigilAgent(REF)
EXAMPLES = sorted(p.name for p in (ROOT / "data" / "scenes").glob("*.png"))

app = FastAPI(title="VigilAgent", version="1.0")


def run_inspection(img: np.ndarray) -> dict:
    from app.storage import persist
    rep = AGENT.inspect(img)
    shown = annotate(img, rep) if rep["verdict"] != "HUMAN_REVIEW" else img
    ok, buf = cv2.imencode(".jpg", shown)
    rep["annotated_jpeg_b64"] = (
        base64.b64encode(buf).decode() if ok else None)
    try:
        rep["storage"] = persist(
            {k: v for k, v in rep.items() if k != "annotated_jpeg_b64"},
            buf.tobytes() if ok else None)
    except Exception as e:  # storage must never fail an inspection
        rep["storage"] = {"stored": False, "reason": f"storage error: {e}"}
    return rep


@app.get("/health")
def health():
    return {"status": "ok", "opencv": cv2.__version__}


@app.post("/inspect")
async def inspect(file: UploadFile = File(...)):
    data = np.frombuffer(await file.read(), np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        return JSONResponse({"error": "undecodable image"}, status_code=400)
    return run_inspection(img)


@app.get("/inspect/example/{name}")
def inspect_example(name: str):
    p = ROOT / "data" / "scenes" / name
    if not p.exists():
        return JSONResponse({"error": "unknown example"}, status_code=404)
    return run_inspection(cv2.imread(str(p)))


@app.get("/", response_class=HTMLResponse)
def home():
    options = "".join(f'<option value="{n}">{n}</option>' for n in EXAMPLES)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>VigilAgent — autonomous visual inspection</title></head>
<body style="font-family:system-ui;max-width:880px;margin:2rem auto">
<h1>VigilAgent</h1>
<p>An autonomous inspection agent built on OpenCV 5. It checks a
workstation photo, corrects what it can, re-inspects what it doubts, and
escalates to a human instead of guessing.</p>
<h3>Run a bundled example scene</h3>
<select id="ex">{options}</select>
<button onclick="runEx()">Inspect example</button>
<h3>Or upload a workstation photo</h3>
<input type="file" id="f" accept="image/*">
<button onclick="runUp()">Inspect upload</button>
<pre id="out" style="background:#111;color:#0f0;padding:1rem;overflow:auto"></pre>
<img id="ann" style="max-width:100%">
<script>
async function show(r){{ const j = await r.json();
  document.getElementById('out').textContent =
    JSON.stringify({{verdict:j.verdict, findings:j.findings,
    uncertainties:j.uncertainties, duration_s:j.duration_s,
    trace:j.trace}}, null, 2);
  if (j.annotated_jpeg_b64) document.getElementById('ann').src =
    'data:image/jpeg;base64,' + j.annotated_jpeg_b64; }}
async function runEx(){{ show(await fetch('/inspect/example/' +
  document.getElementById('ex').value)); }}
async function runUp(){{ const fd = new FormData();
  fd.append('file', document.getElementById('f').files[0]);
  show(await fetch('/inspect', {{method:'POST', body:fd}})); }}
</script></body></html>"""

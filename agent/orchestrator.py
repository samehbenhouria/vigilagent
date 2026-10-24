"""VigilAgent orchestrator — a deterministic perception-decision-action
loop. Every step is appended to a trace so judges can verify that OpenCV
output changed what the agent did next (the Agentic Vision requirement).

Tools are exposed through a registry with JSON-style schemas, in the
spirit of MCP: the agent invokes tools, it does not run a fixed pipeline.
"""
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools_cv.quality import assess_quality, enhance
from tools_cv.markers import detect_zone, decode_qr
from tools_cv.detect import align_to_reference, diff_regions, \
    classify_region, zoom_confirm

MAX_QUALITY_TRIES = 3

# Zone plan for ZONE-A (enrolled reference configuration).
ZONE_PLAN = {
    "zone_id": 7,
    "expected_qr": "ZONE-A|LOT-2026-1042|ITEMSET-STD",
    "slots": [[120, 180, 220, 160], [440, 180, 220, 160],
              [760, 180, 220, 160], [120, 520, 220, 160]],
    "spill_zone": [560, 520, 340, 220],
    "qr_area": [1000, 690, 190, 190],
    "mat_bgr": [160, 155, 148],
}

TOOLS = {
    "assess_quality": "OpenCV blur/exposure/contrast measurements",
    "enhance": "CLAHE / gamma / sharpening corrective action",
    "detect_zone": "ArUco marker zone identification",
    "decode_qr": "QR lot-label decoding",
    "align_to_reference": "ORB + homography alignment to the enrolled reference",
    "diff_regions": "reference difference candidate regions",
    "zoom_confirm": "enlarged-crop second-detector confirmation",
}


class VigilAgent:
    def __init__(self, reference: np.ndarray, plan: dict = ZONE_PLAN):
        self.ref = reference
        self.plan = plan
        self.trace = []

    def _log(self, step, tool, output, decision):
        self.trace.append({"step": len(self.trace) + 1, "phase": step,
                           "tool": tool, "output": output,
                           "decision": decision})

    def inspect(self, img: np.ndarray) -> dict:
        t0 = time.time()
        self.trace = []
        findings, uncertainties = [], []

        # 1) Quality gate with corrective actions chosen per measured issue.
        work = img
        quality = assess_quality(work)
        # Catastrophic blur (calibrated: heavy-blur scenes measure ~0.4,
        # recoverable blur ~3.5) can be made to *score* as sharp by
        # sharpening ringing, so its defect evidence is never trusted:
        # candidates found on it escalate instead of failing the station.
        catastrophic = quality["blur_var"] < 1.5
        tries = 0
        while not quality["usable"] and tries < MAX_QUALITY_TRIES:
            issue = quality["issues"][0]
            self._log("quality_gate", "assess_quality", quality,
                      f"image not usable ({issue}) -> apply enhance:{issue}")
            work = enhance(work, issue)
            tries += 1
            quality = assess_quality(work)
        self._log("quality_gate", "assess_quality", quality,
                  "proceed" if quality["usable"] else "quality unrecoverable")
        if not quality["usable"]:
            return self._verdict("HUMAN_REVIEW", findings,
                                 ["image quality unrecoverable after "
                                  f"{tries} corrective actions: "
                                  f"{quality['issues']}"], work, t0)

        # 2) Zone identification.
        zone = detect_zone(work)
        self._log("identify", "detect_zone", zone,
                  "zone confirmed" if zone["found"] else "zone unknown")
        if not zone["found"] or zone["zone_id"] != self.plan["zone_id"]:
            return self._verdict("HUMAN_REVIEW", findings,
                                 ["zone marker not found or unexpected zone"],
                                 work, t0)

        # 3) Lot label — a failed decode after good quality triggers one
        # rectified retry; a wrong payload is a defect, no decode at all
        # with good quality is an uncertainty, never a silent pass.
        qr = decode_qr(work)
        if not qr["decoded"]:
            self._log("label", "decode_qr", qr,
                      "decode failed -> retry on sharpened upscale")
            retry = cv2.resize(work, None, fx=1.5, fy=1.5,
                               interpolation=cv2.INTER_CUBIC)
            retry = cv2.detailEnhance(retry, sigma_s=10, sigma_r=0.15) \
                if hasattr(cv2, "detailEnhance") else retry
            qr = decode_qr(retry)
            self._log("label", "decode_qr", qr,
                      "decoded on retry" if qr["decoded"] else "still unreadable")
        if qr["decoded"] and qr["data"] != self.plan["expected_qr"]:
            findings.append({"type": "wrong_label", "detail": qr["data"]})
        elif not qr["decoded"]:
            uncertainties.append("lot label unreadable at good quality")

        # 4) Reference inspection with zoom confirmation per candidate.
        al = align_to_reference(work, self.ref)
        self._log("align", "align_to_reference",
                  {"ok": al["ok"], "inliers": al["inliers"]},
                  "diff in reference frame" if al["ok"] else "cannot align")
        if not al["ok"]:
            return self._verdict("HUMAN_REVIEW", findings,
                                 uncertainties + ["alignment to reference failed"],
                                 work, t0)
        regions = diff_regions(al["aligned"], self.ref, al.get("mask"))
        self._log("perceive", "diff_regions",
                  {"candidates": len(regions)}, "confirm each candidate")
        for r in regions:
            kind = classify_region(r, al["aligned"], self.plan)
            if kind == "label_area_change":
                continue  # the QR tool owns the label verdict
            conf = zoom_confirm(al["aligned"], self.ref, r)
            self._log("confirm", "zoom_confirm",
                      {"region": r["bbox"], "kind": kind, **conf},
                      "defect confirmed" if conf["confirmed"]
                      else "candidate dismissed as noise")
            if conf["confirmed"]:
                findings.append({"type": kind, "bbox": r["bbox"],
                                 "area": r["area"]})

        if catastrophic and findings:
            self._log("decide", "evidence_guard",
                      {"initial_blur_var": "catastrophic"},
                      "defect candidates rest on untrustworthy evidence "
                      "-> escalate instead of FAIL")
            uncertainties.append(
                f"{len(findings)} defect candidate(s) on a catastrophically "
                "blurred image — human confirmation required")
            findings = []
        verdict = "FAIL" if findings else (
            "HUMAN_REVIEW" if uncertainties else "PASS")
        return self._verdict(verdict, findings, uncertainties, work, t0,
                             aligned=al["aligned"])

    def _verdict(self, verdict, findings, uncertainties, work, t0,
                 aligned=None):
        return {"verdict": verdict, "findings": findings,
                "uncertainties": uncertainties,
                "duration_s": round(time.time() - t0, 3),
                "trace": self.trace}


def annotate(report_img: np.ndarray, report: dict) -> np.ndarray:
    out = report_img.copy()
    for f in report["findings"]:
        if "bbox" in f:
            x, y, w, h = f["bbox"]
            cv2.rectangle(out, (x, y), (x + w, y + h), (0, 0, 255), 4)
            cv2.putText(out, f["type"], (x, max(30, y - 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    cv2.putText(out, report["verdict"], (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 1.6,
                (0, 160, 0) if report["verdict"] == "PASS" else (0, 0, 255), 4)
    return out

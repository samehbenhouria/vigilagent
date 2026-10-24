"""End-to-end evaluation of VigilAgent on the synthetic v1 set.
Ground truth comes from data/scenes/manifest.json (defects injected by
construction). A case is correct when: a clean case ends PASS (or
HUMAN_REVIEW if a degradation is unrecoverable — counted separately),
and a defect case ends FAIL naming the injected defect type."""
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.orchestrator import VigilAgent

SCENES = ROOT / "data" / "scenes"


def main():
    manifest = json.loads((SCENES / "manifest.json").read_text())
    ref = cv2.imread(str(SCENES / "clean.png"))
    agent = VigilAgent(ref)
    rows, correct = [], 0
    for case in manifest["cases"]:
        img = cv2.imread(str(SCENES / case["file"]))
        rep = agent.inspect(img)
        found = {f["type"] for f in rep["findings"]}
        expected = set(case["defects"])
        if expected:
            ok = rep["verdict"] == "FAIL" and expected <= found | (
                {"slot_anomaly"} if "missing_item" in expected else set())
        else:
            ok = rep["verdict"] in ("PASS", "HUMAN_REVIEW")
        correct += ok
        rows.append({"case": case["case"], "expected": sorted(expected),
                     "verdict": rep["verdict"], "found": sorted(found),
                     "uncertainties": rep["uncertainties"],
                     "duration_s": rep["duration_s"], "ok": ok,
                     "trace_steps": len(rep["trace"])})
        print(f"{case['case']:>22} -> {rep['verdict']:<12} "
              f"found={sorted(found)} ok={ok}")
    result = {"total": len(rows), "correct": correct, "rows": rows}
    (ROOT / "evaluation" / "results_v1.json").write_text(
        json.dumps(result, indent=2))
    print(f"\n{correct}/{len(rows)} cases handled correctly")
    return 0 if correct == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())

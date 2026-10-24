"""V2 evaluation: harder core set (must be handled) + challenge set
(reported, misses documented). Writes evaluation/results_v2.json with
per-case detail and summary statistics for the technical report."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agent.orchestrator import VigilAgent

SCENES = ROOT / "data" / "scenes_v2"
REF = ROOT / "data" / "scenes" / "clean.png"

ALIASES = {"missing_item": {"missing_item", "slot_anomaly"},
           "slot_anomaly": {"slot_anomaly", "missing_item"}}


def judge(rep, expected):
    found = {f["type"] for f in rep["findings"]}
    if expected == ["ESCALATE"]:
        return rep["verdict"] == "HUMAN_REVIEW", found
    if not expected:
        return rep["verdict"] == "PASS", found
    ok = rep["verdict"] == "FAIL" and all(
        (ALIASES.get(e, {e}) & found) for e in expected)
    return ok, found


def run_tier(agent, cases):
    rows, passed = [], 0
    for case in cases:
        rep = agent.inspect(cv2.imread(str(SCENES / case["file"])))
        ok, found = judge(rep, case["defects"])
        passed += ok
        rows.append({"case": case["case"], "expected": case["defects"],
                     "verdict": rep["verdict"], "found": sorted(found),
                     "duration_s": rep["duration_s"], "ok": ok})
        print(f"{case['case']:>20} -> {rep['verdict']:<12} "
              f"found={sorted(found)} ok={ok}")
    return rows, passed


def main():
    manifest = json.loads((SCENES / "manifest.json").read_text())
    agent = VigilAgent(cv2.imread(str(REF)))
    core_rows, core_ok = run_tier(agent, manifest["core"])
    ch_rows, ch_ok = run_tier(agent, manifest["challenge"])
    durations = [r["duration_s"] for r in core_rows + ch_rows]
    summary = {
        "core": {"passed": core_ok, "total": len(core_rows), "rows": core_rows},
        "challenge": {"passed": ch_ok, "total": len(ch_rows), "rows": ch_rows},
        "latency_s": {"mean": round(float(np.mean(durations)), 3),
                      "max": round(float(np.max(durations)), 3)},
    }
    (ROOT / "evaluation" / "results_v2.json").write_text(
        json.dumps(summary, indent=2))
    print(f"\ncore {core_ok}/{len(core_rows)} · challenge {ch_ok}/{len(ch_rows)}"
          f" · latency mean {summary['latency_s']['mean']}s max {summary['latency_s']['max']}s")


if __name__ == "__main__":
    main()

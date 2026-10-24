"""Harder evaluation set (v2): geometric transforms, combined defects,
occlusion and limit cases. Two tiers:
- core: the agent is expected to handle every case;
- challenge: reported honestly, misses become documented failure cases.
Ground truth is by construction, as in v1."""
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("gen1", HERE / "gen_scenes.py")
gen1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen1)

OUT = HERE / "scenes_v2"


def rotate(img, deg):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w // 2, h // 2), deg, 1.0)
    return cv2.warpAffine(img, m, (w, h), borderValue=(185, 180, 170))


def translate(img, dx, dy):
    m = np.float32([[1, 0, dx], [0, 1, dy]])
    return cv2.warpAffine(img, m, (img.shape[1], img.shape[0]),
                          borderValue=(185, 180, 170))


def displaced(img):
    out = img.copy()
    x, y, w, h, col, label = gen1.SLOTS[2]  # TOOL shifted partly out of slot
    cv2.rectangle(out, (x, y), (x + w, y + h), (160, 155, 148), -1)
    cv2.rectangle(out, (x, y), (x + w, y + h), (90, 88, 82), 2)
    cv2.rectangle(out, (x + 55, y + 30), (x + 55 + w, y + 30 + h), col, -1)
    cv2.rectangle(out, (x + 55, y + 30), (x + 55 + w, y + 30 + h), (30, 30, 30), 3)
    return out


def marker_occluded(img):
    out = img.copy()
    cv2.rectangle(out, (50, 100), (185, 230), (185, 180, 170), -1)
    return out


def small_stain(img):
    out = img.copy()
    x, y, w, h = gen1.SPILL_ZONE
    cv2.ellipse(out, (x + 80, y + 60), (30, 18), 10, 0, 360, (40, 60, 140), -1)
    return out


def noisy(img):
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 14, img.shape).astype(np.float32)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    clean = gen1.base_scene()
    core = {
        "rotated8": (rotate(clean.copy(), 8), []),
        "translated": (translate(clean.copy(), 35, -25), []),
        "stain_and_missing": (gen1.defect_missing(gen1.defect_stain(clean.copy())),
                              ["stain", "missing_item"]),
        "displaced_item": (displaced(clean.copy()), ["slot_anomaly"]),
        "marker_occluded": (marker_occluded(clean.copy()), ["ESCALATE"]),
        "blank": (np.full((960, 1280, 3), (185, 180, 170), np.uint8), ["ESCALATE"]),
        "heavy_blur": (cv2.GaussianBlur(clean.copy(), (31, 31), 0), ["ESCALATE"]),
        "noisy_clean": (noisy(clean.copy()), []),
    }
    challenge = {
        "small_stain": (small_stain(clean.copy()), ["stain"]),
        "rotated_stain": (rotate(gen1.defect_stain(clean.copy()), -6), ["stain"]),
    }
    manifest = {"core": [], "challenge": []}
    for tier, cases in (("core", core), ("challenge", challenge)):
        for name, (im, defects) in cases.items():
            p = OUT / f"{name}.png"
            cv2.imwrite(str(p), im)
            manifest[tier].append({"case": name, "file": p.name,
                                  "defects": defects})
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote {len(core)} core + {len(challenge)} challenge scenes")


if __name__ == "__main__":
    main()

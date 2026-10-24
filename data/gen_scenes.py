"""Synthetic workstation scenes for VigilAgent evaluation.

A scene is a top-down 'workstation mat' (1280x960): an ArUco marker fixing
the zone identity (id 7 = ZONE-A), four item slots drawn as labelled
coloured items, and a QR label encoding the expected lot string.
Variants inject one labelled defect or one labelled degradation so the
evaluation has ground truth by construction. All art is drawn with
OpenCV itself; no third-party imagery is used.
"""
import io
import json
from pathlib import Path

import cv2
import numpy as np
import qrcode
from PIL import Image

OUT = Path(__file__).parent / "scenes"
ZONE_ID = 7
EXPECTED_QR = "ZONE-A|LOT-2026-1042|ITEMSET-STD"
WRONG_QR = "ZONE-A|LOT-2019-0007|ITEMSET-STD"

# slot: (x, y, w, h, BGR colour, label)
SLOTS = [
    (120, 180, 220, 160, (60, 140, 220), "BOTTLE"),
    (440, 180, 220, 160, (70, 190, 90), "BOX"),
    (760, 180, 220, 160, (200, 120, 60), "TOOL"),
    (120, 520, 220, 160, (150, 80, 190), "JAR"),
]
SPILL_ZONE = (560, 520, 340, 220)  # free area where a spill is a defect


def _qr_img(text: str, size: int = 190) -> np.ndarray:
    qr = qrcode.QRCode(border=2, box_size=8)
    qr.add_data(text)
    qr.make(fit=True)
    pil = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    pil = pil.resize((size, size), Image.NEAREST)
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def base_scene(qr_text: str = EXPECTED_QR) -> np.ndarray:
    img = np.full((960, 1280, 3), (185, 180, 170), np.uint8)  # mat
    cv2.rectangle(img, (40, 90), (1240, 900), (160, 155, 148), -1)
    for (x, y, w, h, col, label) in SLOTS:
        cv2.rectangle(img, (x, y), (x + w, y + h), col, -1)
        cv2.rectangle(img, (x, y), (x + w, y + h), (30, 30, 30), 3)
        cv2.putText(img, label, (x + 18, y + h // 2 + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
    # QR label, bottom-right
    qr = _qr_img(qr_text)
    img[690:690 + qr.shape[0], 1000:1000 + qr.shape[1]] = qr
    cv2.putText(img, "LOT LABEL", (1000, 670), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (30, 30, 30), 2)
    # ArUco zone marker, top-left
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(d, ZONE_ID, 110)
    marker = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    img[110:220, 60:170] = marker
    cv2.putText(img, "ZONE-A", (60, 105), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (30, 30, 30), 2)
    return img


def defect_stain(img):
    out = img.copy()
    x, y, w, h = SPILL_ZONE
    cv2.ellipse(out, (x + w // 2, y + h // 2), (120, 70), 25, 0, 360,
                (40, 60, 140), -1)  # dark amber spill
    return out


def defect_missing(img):
    out = img.copy()
    x, y, w, h, _, _ = SLOTS[1]  # BOX slot emptied, mat colour restored
    cv2.rectangle(out, (x, y), (x + w, y + h), (160, 155, 148), -1)
    cv2.rectangle(out, (x, y), (x + w, y + h), (90, 88, 82), 2)
    return out


def defect_foreign(img):
    out = img.copy()
    cv2.circle(out, (620, 420), 55, (30, 30, 200), -1)  # unknown red object
    return out


def degrade(img, kind):
    if kind == "blur":
        return cv2.GaussianBlur(img, (15, 15), 0)
    if kind == "low_contrast":
        return cv2.convertScaleAbs(img, alpha=0.45, beta=70)
    if kind == "underexposed":
        return cv2.convertScaleAbs(img, alpha=0.35, beta=0)
    if kind == "perspective":
        h, w = img.shape[:2]
        src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
        dst = np.float32([[90, 60], [w - 140, 0], [w - 40, h - 90], [30, h - 30]])
        m = cv2.getPerspectiveTransform(src, dst)
        return cv2.warpPerspective(img, m, (w, h),
                                   borderValue=(185, 180, 170))
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    clean = base_scene()
    cases = {
        "clean": clean,
        "stain": defect_stain(clean.copy()),
        "missing_item": defect_missing(clean.copy()),
        "foreign_object": defect_foreign(clean.copy()),
        "wrong_label": base_scene(WRONG_QR),
        "clean_blur": degrade(clean.copy(), "blur"),
        "clean_low_contrast": degrade(clean.copy(), "low_contrast"),
        "clean_underexposed": degrade(clean.copy(), "underexposed"),
        "clean_perspective": degrade(clean.copy(), "perspective"),
        "stain_blur": degrade(defect_stain(clean.copy()), "blur"),
    }
    truth = {
        "clean": [], "stain": ["stain"], "missing_item": ["missing_item"],
        "foreign_object": ["foreign_object"],
        "wrong_label": ["wrong_label"], "clean_blur": [],
        "clean_low_contrast": [], "clean_underexposed": [],
        "clean_perspective": [], "stain_blur": ["stain"],
    }
    for name, im in cases.items():
        p = OUT / f"{name}.png"
        cv2.imwrite(str(p), im)
        manifest.append({"case": name, "file": p.name,
                         "defects": truth[name]})
    (OUT / "manifest.json").write_text(json.dumps(
        {"zone_id": ZONE_ID, "expected_qr": EXPECTED_QR,
         "slots": [list(s[:4]) for s in SLOTS], "cases": manifest},
        indent=2))
    print(f"wrote {len(manifest)} scenes to {OUT}")


if __name__ == "__main__":
    main()

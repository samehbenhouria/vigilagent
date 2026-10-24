"""Defect detection tools — OpenCV 5.

Alignment (ORB + homography) puts the inspected image into the reference
frame; a thresholded absolute difference then yields candidate defect
regions, which the zone plan classifies (slot anomaly / stain in a free
area / foreign object / label area). A second, independent zoom check
confirms or dismisses each candidate before the agent may call it a
defect — a single detector never produces a FAIL on its own.
"""
import cv2
import numpy as np

DIFF_THRESH = 30
MIN_AREA = 900


def align_to_reference(img: np.ndarray, ref: np.ndarray) -> dict:
    orb = cv2.ORB_create(4000)
    kp1, des1 = orb.detectAndCompute(img, None)
    kp2, des2 = orb.detectAndCompute(ref, None)
    if des1 is None or des2 is None:
        return {"ok": False, "aligned": img, "inliers": 0}
    matches = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(des1, des2, k=2)
    good = [m for m, n in (p for p in matches if len(p) == 2)
            if m.distance < 0.75 * n.distance]
    if len(good) < 12:
        return {"ok": False, "aligned": img, "inliers": len(good)}
    src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    h, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if h is None:
        return {"ok": False, "aligned": img, "inliers": int(mask.sum()) if mask is not None else 0}
    aligned = cv2.warpPerspective(img, h, (ref.shape[1], ref.shape[0]))
    # Valid-area mask: pixels warped in from outside the source frame are
    # not evidence (rotation/translation wedges). Eroded so border blends
    # never become candidate defects.
    ones = np.full(img.shape[:2], 255, np.uint8)
    valid = cv2.warpPerspective(ones, h, (ref.shape[1], ref.shape[0]))
    valid = cv2.erode(valid, cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (25, 25)))
    return {"ok": True, "aligned": aligned, "mask": valid,
            "inliers": int(mask.sum()) if mask is not None else len(good)}


def diff_regions(aligned: np.ndarray, ref: np.ndarray,
                 mask: np.ndarray = None) -> list:
    diff = cv2.absdiff(aligned, ref)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, bw = cv2.threshold(gray, DIFF_THRESH, 255, cv2.THRESH_BINARY)
    if mask is not None:
        bw = cv2.bitwise_and(bw, mask)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    bw = cv2.morphologyEx(bw, cv2.MORPH_CLOSE,
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    regions = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < MIN_AREA:
            continue
        x, y, w, h = cv2.boundingRect(c)
        regions.append({"bbox": [x, y, w, h], "area": float(area),
                        "center": [x + w // 2, y + h // 2]})
    return sorted(regions, key=lambda r: -r["area"])


def _inside(cx, cy, box):
    x, y, w, h = box
    return x <= cx <= x + w and y <= cy <= y + h


def classify_region(region: dict, aligned: np.ndarray, plan: dict) -> str:
    cx, cy = region["center"]
    for i, slot in enumerate(plan["slots"]):
        if _inside(cx, cy, slot):
            x, y, w, h = slot
            roi = aligned[y:y + h, x:x + w]
            mean = roi.mean(axis=(0, 1))  # BGR
            mat = np.array(plan.get("mat_bgr", [160, 155, 148]))
            if np.abs(mean - mat).mean() < 18:
                return "missing_item"
            return "slot_anomaly"
    if _inside(cx, cy, plan["spill_zone"]):
        return "stain"
    if _inside(cx, cy, plan["qr_area"]):
        return "label_area_change"
    return "foreign_object"


def zoom_confirm(aligned: np.ndarray, ref: np.ndarray,
                 region: dict) -> dict:
    """Independent second look at an enlarged crop: a real defect keeps a
    strong mean difference and structured edges; alignment noise does not."""
    x, y, w, h = region["bbox"]
    pad = 12
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(aligned.shape[1], x + w + pad), min(aligned.shape[0], y + h + pad)
    a = aligned[y0:y1, x0:x1]
    r = ref[y0:y1, x0:x1]
    if a.size == 0:
        return {"confirmed": False, "mean_diff": 0.0}
    big_a = cv2.resize(a, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    big_r = cv2.resize(r, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    mean_diff = float(cv2.absdiff(big_a, big_r).mean())
    return {"confirmed": mean_diff > 12.0, "mean_diff": round(mean_diff, 2)}

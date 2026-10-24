"""Zone identification (ArUco) and lot label verification (QR) — OpenCV 5."""
import cv2
import numpy as np


def detect_zone(img: np.ndarray) -> dict:
    d = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    det = cv2.aruco.ArucoDetector(d, cv2.aruco.DetectorParameters())
    corners, ids, _ = det.detectMarkers(img)
    if ids is None:
        return {"found": False, "zone_id": None, "corners": None}
    return {"found": True, "zone_id": int(ids.flatten()[0]),
            "corners": corners[0].reshape(-1, 2).tolist()}


def decode_qr(img: np.ndarray) -> dict:
    det = cv2.QRCodeDetector()
    data, points, _ = det.detectAndDecode(img)
    return {"decoded": bool(data), "data": data or None,
            "points": None if points is None else points.reshape(-1, 2).tolist()}

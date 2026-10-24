"""Image quality gate — OpenCV 5 measurements that drive the agent's
corrective actions. Every metric is a plain float so the orchestrator can
log it in the trace and branch on it."""
import cv2
import numpy as np

# Thresholds calibrated on the synthetic v1 set (2026-10-23): clean scenes
# measure blur>=100, contrast_std>=30, mean in [150,160]; degraded scenes
# measure blur=3.5, contrast_std<=15, underexposed mean=54. Thresholds sit
# midway in each gap. Real-photo revalidation is scheduled before freeze.
BLUR_MIN = 100.0         # Laplacian variance below this = too blurry
CONTRAST_MIN = 22.0     # gray std below this = too flat
EXPOSURE_LO, EXPOSURE_HI = 80.0, 215.0  # mean gray outside = bad exposure


def assess_quality(img: np.ndarray) -> dict:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(gray.std())
    exposure = float(gray.mean())
    issues = []
    if blur < BLUR_MIN:
        issues.append("blur")
    if contrast < CONTRAST_MIN:
        issues.append("low_contrast")
    if exposure < EXPOSURE_LO:
        issues.append("underexposed")
    elif exposure > EXPOSURE_HI:
        issues.append("overexposed")
    return {
        "blur_var": round(blur, 2),
        "contrast_std": round(contrast, 2),
        "exposure_mean": round(exposure, 2),
        "issues": issues,
        "usable": len(issues) == 0,
    }


def enhance(img: np.ndarray, issue: str) -> np.ndarray:
    """One corrective action per measured issue — chosen by the agent."""
    if issue == "low_contrast":
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    if issue == "underexposed":
        return cv2.convertScaleAbs(img, alpha=1.6, beta=25)
    if issue == "overexposed":
        return cv2.convertScaleAbs(img, alpha=0.7, beta=0)
    if issue == "blur":
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        return cv2.filter2D(img, -1, kernel)
    return img

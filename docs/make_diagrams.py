"""Generate the two submission diagrams as PNGs with PIL:
1) architecture.png — OpenCV 5 + AWS components.
2) agent_workflow.png — perception -> decision -> action loop
   (Agentic Vision Award evidence). v2 geometry: taller boxes, routed
   arrows that never cross a box."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def T(size, bold=False):
    return ImageFont.truetype(FB if bold else FR, size)


def box(d, xy, fill, outline="#333333"):
    d.rounded_rectangle(xy, radius=14, fill=fill, outline=outline, width=3)


def ctext(d, cx, y, txt, font, color="#111111"):
    d.text((cx - d.textlength(txt, font=font) / 2, y), txt, font=font, fill=color)


def arrow(d, pts, color="#333333", width=4):
    d.line(pts, fill=color, width=width, joint="curve")
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    ang = math.atan2(y2 - y1, x2 - x1)
    for da in (2.75, -2.75):
        d.line([(x2, y2), (x2 + 17 * math.cos(ang + da),
                           y2 + 17 * math.sin(ang + da))],
               fill=color, width=width)


def architecture():
    W, H = 1560, 1020
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 22), "VigilAgent — Architecture (OpenCV 5 + AWS)",
           font=T(30, True), fill="#111111")

    # Browser
    box(d, (40, 110, 390, 250), "#EAF2FB")
    ctext(d, 215, 128, "Judge / User browser", T(21, True))
    ctext(d, 215, 168, "demo page, image upload,", T(18))
    ctext(d, 215, 196, "annotated result + agent trace", T(18))

    # API Gateway
    box(d, (520, 110, 1040, 250), "#EFEFEF")
    ctext(d, 780, 128, "Amazon API Gateway (HTTP API)", T(21, True))
    ctext(d, 780, 168, "single public entry point", T(18))
    ctext(d, 780, 196, "deployed with AWS SAM — infra/template.yaml", T(18))

    # Lambda
    box(d, (520, 320, 1040, 800), "#E9F7EC")
    ctext(d, 780, 338, "AWS Lambda — ARM64 / Graviton", T(21, True))
    ctext(d, 780, 372, "container image: FastAPI + OpenCV 5.0.0", T(17))
    ctext(d, 780, 396, "served via Lambda Web Adapter", T(17))
    box(d, (555, 415, 1005, 520), "#FFFFFF")
    ctext(d, 780, 430, "VigilAgent orchestrator", T(20, True))
    ctext(d, 780, 468, "deterministic agent loop · full JSON trace", T(18))
    box(d, (555, 545, 1005, 770), "#FFFFFF")
    ctext(d, 780, 558, "OpenCV 5 tool registry (MCP-style)", T(20, True))
    tools = ["assess_quality · enhance",
             "(CLAHE / gamma / sharpen)",
             "detect_zone (ArUco) · decode_qr",
             "align_to_reference (ORB + homography)",
             "diff_regions · classify · zoom_confirm",
             "storage: persist evidence (boto3)"]
    for i, t in enumerate(tools):
        ctext(d, 780, 598 + i * 28, t, T(16))

    # AWS stores
    for (y, title, l1, l2) in [
            (320, "S3 — evidence store", "report JSON, traces,", "annotated images"),
            (500, "DynamoDB — inspection index", "verdict, findings count,", "timestamp, S3 prefix"),
            (680, "CloudWatch", "function logs", "and metrics")]:
        box(d, (1160, y, 1520, y + 120), "#FDECEC")
        ctext(d, 1340, y + 14, title, T(19, True))
        ctext(d, 1340, y + 54, l1, T(17))
        ctext(d, 1340, y + 80, l2, T(17))

    # Local run
    box(d, (40, 470, 390, 610), "#FDF3E3")
    ctext(d, 215, 488, "Local / container run", T(21, True))
    ctext(d, 215, 528, "same code via uvicorn —", T(18))
    ctext(d, 215, 556, "judges may self-host;", T(18))
    ctext(d, 215, 584, "AWS persistence off", T(18))

    arrow(d, [(390, 180), (520, 180)])                       # browser -> gateway
    arrow(d, [(780, 250), (780, 320)])                      # gateway -> lambda
    arrow(d, [(1040, 380), (1160, 380)])                     # lambda -> S3
    arrow(d, [(1040, 560), (1160, 560)])                     # lambda -> DynamoDB
    arrow(d, [(1040, 740), (1160, 740)])                     # lambda -> CloudWatch
    d.line([(390, 540), (470, 540), (470, 700), (555, 700)], fill="#B07D2B", width=3)
    d.text((52, 640), "same container image", font=T(16), fill="#B07D2B")
    img.save(OUT / "architecture.png")
    print("architecture.png")


def workflow():
    W, H = 1560, 1060
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 22), "VigilAgent — agent workflow: visual output changes the next action",
           font=T(26, True), fill="#111111")
    steps = [
        ("1 · PLAN", ["ArUco marker identifies the zone;",
                      "its enrolled plan selects tools & thresholds"], "#EAF2FB"),
        ("2 · QUALITY GATE", ["blur / contrast / exposure measured by OpenCV",
                              "fail → corrective action chosen per issue",
                              "(CLAHE, gamma, sharpen) → re-measure, ≤ 3 rounds"], "#FDF3E3"),
        ("3 · PERCEIVE", ["QR lot label · ORB alignment to the reference",
                          "reference diff · region classification"], "#E9F7EC"),
        ("4 · DOUBT → RE-INSPECT", ["low confidence triggers a DIFFERENT action:",
                                    "rectified QR retry · zoom + second detector",
                                    "confirming or dismissing each candidate"], "#F3EAFB"),
        ("5 · DECIDE", ["PASS · FAIL (confirmed defect) · HUMAN_REVIEW",
                        "critical or unresolved cases always escalate"], "#FDECEC"),
        ("6 · REPORT", ["annotated image, findings, full JSON trace",
                        "stored to S3 + DynamoDB on AWS, returned locally"], "#EFEFEF"),
    ]
    x0, x1, y, bh, pitch = 300, 1300, 92, 128, 152
    centers = []
    for title, lines, fill in steps:
        box(d, (x0, y, x1, y + bh), fill)
        ctext(d, (x0 + x1) // 2, y + 10, title, T(21, True))
        for j, line in enumerate(lines):
            ctext(d, (x0 + x1) // 2, y + 50 + j * 27, line, T(18))
        centers.append(y + bh // 2)
        if y > 92:
            arrow(d, [((x0 + x1) // 2, y - 22), ((x0 + x1) // 2, y - 3)])
        y += pitch
    # correction loop: self-loop on step 2 (left side)
    y2 = centers[1]
    d.line([(x0, y2), (215, y2), (215, y2 - 34), (x0, y2 - 34)],
           fill="#B07D2B", width=4)
    arrow(d, [(215, y2 - 34), (x0, y2 - 34)], color="#B07D2B")
    d.text((48, y2 - 62), "correction loop", font=T(17), fill="#B07D2B")
    # re-inspection loop: step 4 back up to step 3 (left side, wider)
    y3, y4 = centers[2], centers[3]
    d.line([(x0, y4), (150, y4), (150, y3), (x0, y3)], fill="#7A4FA3", width=4)
    arrow(d, [(150, y3), (x0, y3)], color="#7A4FA3")
    d.text((48, (y3 + y4) // 2 - 30), "re-inspection\nloop", font=T(17), fill="#7A4FA3")
    img.save(OUT / "agent_workflow.png")
    print("agent_workflow.png")


if __name__ == "__main__":
    architecture()
    workflow()

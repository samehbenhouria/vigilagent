## Inspiration
Small businesses run visual compliance checks — is the workstation complete, clean, correctly labelled? — from memory. Checks get skipped, and when something is wrong there is no record of what was seen or decided. We wanted an inspector that behaves the way a careful human does: look, doubt, look again differently, and ask for help when it cannot be sure.

## What it does
**VigilAgent** inspects a photograph of a workstation or storage zone and returns a verdict — **PASS**, **FAIL**, or **HUMAN_REVIEW** — with visual evidence and a complete decision trace.

- An **ArUco marker** identifies the zone; the zone's enrolled plan selects the inspection tools and thresholds.
- A **quality gate** measures blur, contrast and exposure. A failing image is corrected with the action matching the measured problem (CLAHE, gamma, sharpening) and re-measured — up to three rounds. An image that stays unusable is never judged.
- The agent decodes the **QR lot label**, aligns the photo to the enrolled reference (**ORB + homography**), differences it, and classifies candidate defects: missing item, displaced item, stain, foreign object, wrong label.
- **Every candidate must survive a second, independent zoomed look** before it can fail the station. A label that will not decode is retried after rectification.
- Unresolved or critical cases **escalate to a human**, with the reason written in the trace.

## How we built it
OpenCV 5.0.0 is the only vision engine — no trained model, no external AI API, fully reproducible from pinned dependencies. The agent is a deterministic orchestrator invoking OpenCV tools through an MCP-style registry; every tool call and branch is logged to a JSON trace, which is how judges can verify that visual output changed the agent's next action.

The web endpoint is FastAPI in a container that runs identically in three places: locally under uvicorn, stand-alone in Docker, and on **AWS Lambda (ARM64/Graviton)** behind **API Gateway**, deployed with **AWS SAM**. On AWS, each report and its annotated evidence persist to **S3** with a **DynamoDB** index and **CloudWatch** observability.

Evaluation is generated, not cherry-picked: our own code builds workstation scenes with ground truth by construction, injects four defect families and five degradations, and scores the agent end-to-end — **10/10 cases on set v1, 8/8 core and 2/2 challenge cases on the harder set v2**, including the failure cases we found and fixed (phantom defects from rotation borders, and sharpening artifacts that fooled the quality metric — both documented in the report).

## Challenges we ran into
- Rotation borders produced large phantom "foreign objects" — fixed by restricting the reference difference to a valid-area mask warped with the same homography.
- Catastrophic blur could be sharpened until it *scored* as sharp while containing no evidence — fixed with an evidence guard: candidates resting on catastrophic input escalate instead of failing the station.
- Aggressive photometric correction shifted colours and caused a false FAIL — the shipped agent corrects conservatively, one action per round, re-measuring between rounds.

## Accomplishments that we're proud of
An inspection agent whose caution is measurable: it recovers borderline images, refuses to judge destroyed ones, and never lets a single detector fail a workstation alone.

## What's next
Video-stream inspection, multi-zone enrolment from a phone walkthrough, and an on-device variant for stations without connectivity.

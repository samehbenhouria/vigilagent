# Video script — VigilAgent demo (target 4 min 30 s, hard limit 5 min)
Format: screen capture of the live demo + architecture slides + narration.
The competition requires the video to show the team, the working app, the
architecture and the principal results — the segments below map 1:1.

| Time | Visual | Narration (essence) |
|---|---|---|
| 0:00–0:30 | Team slide: name, solo builder, Longueuil (Québec); photo/avatar of Sameh if he provides one, otherwise name + role card | "I'm Sameh Ben Houria. I built VigilAgent, an autonomous visual inspection agent, for the OpenCV AI Competition 2026." |
| 0:30–1:00 | Problem: photo of a messy workstation scene (our stain scene), checklist visual | "Small businesses check workstations from memory. Checks get skipped, and nothing is recorded. VigilAgent turns one photo into a traceable inspection." |
| 1:00–2:30 | LIVE DEMO on the endpoint: run clean (PASS) → stain (FAIL, box drawn, trace scrolls) → blurred scene (agent corrects, re-measures, then PASS) → low-contrast scene (escalates HUMAN_REVIEW) | Walk the trace aloud: "Watch the trace — the blur measurement fails, so the agent chooses sharpening and measures again. The stain candidate is only failed after a second, zoomed detector confirms it. And here it refuses to judge — it escalates to a human." |
| 2:30–3:15 | Architecture diagram + agent workflow diagram | "OpenCV 5 is the only vision engine… the same container runs locally and on AWS Lambda on Graviton, behind API Gateway, with S3 evidence and a DynamoDB index, deployed by SAM." Show the two loops (correction, re-inspection) explicitly — this is the Agentic Vision evidence. |
| 3:15–4:15 | Results table: v1 10/10, v2 core 8/8 + challenge 2/2, latency; failure-case cards F1/F4/F5 | "Evaluation is generated, not cherry-picked… two real bugs the evaluation caught before you did: phantom defects from rotation borders, and sharpening that fooled the quality metric. Both fixed, both documented." |
| 4:15–4:45 | Limitations + closing on demo page | "One zone, still images, four defect families — and a rule we kept throughout: the agent never silently passes what it could not verify. Thank you." |

Production notes:
- Record the demo against the deployed AWS endpoint if available, else the
  identical local container (state which in the description, honestly).
- Captions on (accessibility is a judged UX criterion).
- Upload unlisted/public on YouTube; paste the URL in Devpost step 3.

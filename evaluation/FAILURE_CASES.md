# Failure cases and design lessons (evaluation evidence — updated as testing proceeds)

## F1 — Aggressive photometric correction invalidates the colour reference diff (found 2026-10-23, experiment reverted)
Variant tested: at the quality gate, apply one corrective action per measured
issue in a single round (e.g. gamma + CLAHE together for an underexposed,
low-contrast image) instead of one conservative correction per round.
Result: `clean_underexposed` recovered "usable" quality scores but the shifted
colours produced two false defects (`foreign_object`, `slot_anomaly`) against
the enrolled reference — score dropped from 10/10 to 9/10 with a false FAIL,
the worst error class for an inspection system.
Decision kept: one conservative correction per round, re-measure between
rounds, and escalate to a human when quality stays unrecoverable
(`clean_low_contrast`, `clean_underexposed` → HUMAN_REVIEW). An inspection
agent must prefer "I cannot judge this image" over a confident wrong verdict.

## F2 — Unrecoverable degradations escalate, by design
Gaussian blur at the tested strength destroys the QR payload; sharpening
recovers enough structure for the scene checks (`clean_blur` → PASS) but this
is near the recovery limit. Heavier blur, occlusion of the zone marker, or a
failed reference alignment all terminate in HUMAN_REVIEW with the reason in
the trace — measured behaviour, not a silent pass.

## F4 — Rotation borders became phantom defects (found and fixed 2026-10-23)
An 8°-rotated clean scene produced four large "foreign object" regions —
all hugging the image borders: the wedges that rotation fills outside the
source frame. Mean differences were large (~76), so zoom confirmation
passed them. Fix: alignment now warps a valid-area mask with the same
homography and the reference difference is restricted to the eroded
mask. After the fix: rotated and translated clean scenes PASS, and a
rotated stain is reported as exactly one stain.

## F5 — Sharpening ringing defeated the quality metric AND the confirmer (found and fixed 2026-10-23)
A catastrophically blurred scene (initial Laplacian variance 0.44) was
sharpened until it passed the quality gate; alignment then "succeeded"
on ringing artifacts (105 inliers) and soft regions passed zoom
confirmation just above threshold (mean diff 12.0–14.2 vs a 12.0 cut).
The agent returned FAIL on a scene it should have escalated. Fix: an
evidence guard — when the *original* blur measurement is catastrophic
(< 1.5; recoverable blur measures ≈ 3.5), defect candidates are treated
as unconfirmed and the case escalates to HUMAN_REVIEW. The real stain
under moderate blur (variance 3.55, zoom mean diff 41.9) still FAILs
correctly: the guard separates by evidence quality, not by verdict.

## F3 — Synthetic-set limitation (declared)
All v1 metrics are measured on program-generated scenes whose defects are
injected by construction. Colours, lighting and geometry are far simpler
than real workstation photographs. Real-photo validation is scheduled
before the scope freeze; any threshold change it forces will be recorded
here with before/after numbers.

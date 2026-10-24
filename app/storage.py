"""Optional AWS persistence. When VIGIL_BUCKET / VIGIL_TABLE are set (the
SAM deployment sets them), each inspection's report JSON and annotated
image are stored in S3 and indexed in DynamoDB. Locally the variables are
unset and storage is a no-op, so the exact same code runs everywhere."""
import json
import os
import time
import uuid

BUCKET = os.environ.get("VIGIL_BUCKET")
TABLE = os.environ.get("VIGIL_TABLE")


def persist(report: dict, annotated_jpeg: bytes | None) -> dict:
    if not BUCKET:
        return {"stored": False, "reason": "local mode (VIGIL_BUCKET unset)"}
    import boto3  # available in the deployment image; lazy import locally

    inspection_id = uuid.uuid4().hex[:16]
    prefix = f"inspections/{time.strftime('%Y%m%d')}/{inspection_id}"
    s3 = boto3.client("s3")
    s3.put_object(Bucket=BUCKET, Key=f"{prefix}/report.json",
                  Body=json.dumps(report).encode(),
                  ContentType="application/json")
    if annotated_jpeg:
        s3.put_object(Bucket=BUCKET, Key=f"{prefix}/annotated.jpg",
                      Body=annotated_jpeg, ContentType="image/jpeg")
    if TABLE:
        boto3.resource("dynamodb").Table(TABLE).put_item(Item={
            "inspection_id": inspection_id,
            "ts": int(time.time()), "verdict": report["verdict"],
            "findings": len(report["findings"]),
            "s3_prefix": prefix})
    return {"stored": True, "inspection_id": inspection_id,
            "s3_prefix": prefix}

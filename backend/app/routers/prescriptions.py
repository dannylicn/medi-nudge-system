"""
Prescription scan routes — image upload, OCR review, confirm/reject.
Images are NEVER returned as raw bytes or raw file paths.
All image access goes through signed URLs (local path in dev; S3 signed URL in prod).
"""
import os
import boto3
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import PrescriptionScan, ExtractedMedicationField, User
from app.schemas.schemas import PrescriptionScanOut, ExtractedFieldUpdate
from app.services.ocr_service import ingest_image, confirm_scan, reject_scan, generate_image_url

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

router = APIRouter(prefix="/api/prescriptions", tags=["prescriptions"])


@router.post("", response_model=PrescriptionScanOut, status_code=201)
async def upload_prescription(
    request: Request,
    patient_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image exceeds 10 MB limit")

    client_ip = request.client.host if request.client else None
    scan = ingest_image(db=db, patient_id=patient_id, image_bytes=content, source="web_upload", uploaded_by_ip=client_ip)
    base_url = str(request.base_url).rstrip("/")
    out = PrescriptionScanOut.model_validate(scan)
    out.image_url = generate_image_url(scan, base_url)
    return out


@router.get("", response_model=list[PrescriptionScanOut])
def list_scans(
    patient_id: int | None = None,
    status: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(PrescriptionScan)
    if patient_id:
        q = q.filter(PrescriptionScan.patient_id == patient_id)
    if status:
        q = q.filter(PrescriptionScan.status == status)
    scans = q.order_by(PrescriptionScan.uploaded_at.desc()).all()
    base_url = str(request.base_url).rstrip("/") if request else ""
    result = []
    for scan in scans:
        out = PrescriptionScanOut.model_validate(scan)
        out.image_url = generate_image_url(scan, base_url)
        result.append(out)
    return result


@router.get("/{scan_id}", response_model=PrescriptionScanOut)
def get_scan(
    scan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    scan = db.query(PrescriptionScan).filter(PrescriptionScan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    base_url = str(request.base_url).rstrip("/")
    out = PrescriptionScanOut.model_validate(scan)
    out.image_url = generate_image_url(scan, base_url)
    return out


@router.get("/{scan_id}/image")
def serve_scan_image(
    scan_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),  # Auth required — no public access
):
    """Serve the raw image bytes (local dev only). In production S3 pre-signed URLs are used."""
    from fastapi.responses import Response, RedirectResponse
    from app.core.config import settings
    scan = db.query(PrescriptionScan).filter(PrescriptionScan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if settings.AWS_S3_BUCKET_NAME and scan.image_path and not os.path.isabs(scan.image_path):
        client = boto3.client("s3", region_name=settings.AWS_REGION)
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_S3_BUCKET_NAME, "Key": scan.image_path},
            ExpiresIn=900,
        )
        return RedirectResponse(url=url, status_code=302)
    if not scan.image_path or not os.path.exists(scan.image_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    with open(scan.image_path, "rb") as f:
        content = f.read()
    return Response(content=content, media_type="image/jpeg")


@router.patch("/{scan_id}/fields/{field_id}", response_model=dict)
def update_field(
    scan_id: int,
    field_id: int,
    payload: ExtractedFieldUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    field = db.query(ExtractedMedicationField).filter(
        ExtractedMedicationField.id == field_id,
        ExtractedMedicationField.scan_id == scan_id,
    ).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    field.is_corrected = True
    field.corrected_value = payload.corrected_value
    db.commit()
    return {"id": field.id, "corrected_value": field.corrected_value}


@router.patch("/{scan_id}/confirm", response_model=PrescriptionScanOut)
def confirm_prescription_scan(
    scan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    scan = db.query(PrescriptionScan).filter(PrescriptionScan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    try:
        scan = confirm_scan(db=db, scan=scan, confirmed_by=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    base_url = str(request.base_url).rstrip("/")
    out = PrescriptionScanOut.model_validate(scan)
    out.image_url = generate_image_url(scan, base_url)
    return out


@router.patch("/{scan_id}/reject", response_model=PrescriptionScanOut)
def reject_prescription_scan(
    scan_id: int,
    request: Request,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    scan = db.query(PrescriptionScan).filter(PrescriptionScan.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    try:
        scan = reject_scan(db=db, scan=scan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    base_url = str(request.base_url).rstrip("/")
    out = PrescriptionScanOut.model_validate(scan)
    out.image_url = generate_image_url(scan, base_url)
    return out

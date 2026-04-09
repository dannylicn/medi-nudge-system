"""
Prescription OCR service.
Primary: GPT-4o Vision.  Fallback: Tesseract.
"""
import hashlib
import io
import json
import logging
import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import (
    PrescriptionScan, ExtractedMedicationField,
    Medication, PatientMedication, DispensingRecord,
    SCAN_VALID_TRANSITIONS,
)

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.75

FIELD_NAMES = [
    "medication_name", "generic_name", "dosage", "frequency",
    "refill_days", "prescriber", "clinic", "dispense_date",
    "expiry_date", "instructions", "warnings",
]


def _parse_ocr_fields(raw_fields: list) -> list:
    """Normalise raw OCR field dicts — returns the list as-is after type coercion."""
    result = []
    for f in raw_fields:
        result.append({
            "field_name": str(f.get("field_name", "")),
            "value": str(f.get("value", "")),
            "confidence": float(f.get("confidence", 0.0)),
        })
    return result


def ingest_image(
    db: Session,
    patient_id: int,
    image_bytes: bytes,
    source: str = "web_upload",
    uploaded_by_ip: str | None = None,
) -> PrescriptionScan:
    """Store image, create PrescriptionScan, run OCR, store fields."""
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    hashed_ip = hashlib.sha256(uploaded_by_ip.encode()).hexdigest() if uploaded_by_ip else None

    # Deduplication
    existing = (
        db.query(PrescriptionScan)
        .filter(
            PrescriptionScan.patient_id == patient_id,
            PrescriptionScan.image_hash == image_hash,
        )
        .first()
    )
    if existing:
        return existing

    # Store encrypted at rest — for v1 we write to local path; swap to S3 in prod
    storage_dir = os.path.join(settings.MEDIA_STORAGE_PATH, "prescriptions", str(patient_id))
    os.makedirs(storage_dir, exist_ok=True)
    filename = f"{image_hash[:16]}_{int(datetime.utcnow().timestamp())}.jpg"
    image_path = os.path.join(storage_dir, filename)
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    scan = PrescriptionScan(
        patient_id=patient_id,
        image_path=image_path,
        image_hash=image_hash,
        source=source,
        status="pending",
        uploaded_by_ip=hashed_ip,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    # Run OCR
    extracted, engine = _run_ocr(image_bytes)
    scan.raw_extracted_json = extracted
    scan.ocr_engine = engine

    # Store fields
    has_low_confidence = False
    for field_name in FIELD_NAMES:
        value = extracted.get(field_name)
        confidence = extracted.get(f"{field_name}_confidence", 1.0 if value else 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = float(confidence)
        field = ExtractedMedicationField(
            scan_id=scan.id,
            field_name=field_name,
            extracted_value=str(value) if value is not None else None,
            confidence=confidence,
        )
        db.add(field)
        if value is not None and confidence < CONFIDENCE_THRESHOLD:
            has_low_confidence = True

    scan.status = "review"  # Always requires coordinator sign-off (v1 policy)
    db.commit()
    db.refresh(scan)
    return scan


def _run_ocr(image_bytes: bytes) -> tuple[dict, str]:
    """Try GPT-4o Vision; fall back to Tesseract."""
    if settings.OPENAI_API_KEY:
        try:
            return _gpt4o_ocr(image_bytes), "gpt4o_vision"
        except Exception as exc:
            logger.warning("GPT-4o Vision OCR failed, falling back to Tesseract: %s", exc)
    return _tesseract_ocr(image_bytes), "tesseract"


def _gpt4o_ocr(image_bytes: bytes) -> dict:
    import base64
    from openai import OpenAI

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    system_prompt = (
        "You are a pharmacy data extraction assistant. Extract structured fields from the prescription "
        "or medicine label image. Return ONLY a valid JSON object with these keys: "
        "medication_name, generic_name, dosage, frequency, refill_days (integer), prescriber, clinic, "
        "dispense_date (YYYY-MM-DD), expiry_date (YYYY-MM-DD), instructions, warnings (list of strings). "
        "For each field also include a confidence key: <fieldname>_confidence (float 0.0-1.0). "
        "Use null for fields not found."
    )

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    }
                ],
            },
        ],
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    text = response.choices[0].message.content
    return json.loads(text)


def _tesseract_ocr(image_bytes: bytes) -> dict:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        raw_text = pytesseract.image_to_string(img)
        # Heuristic extraction — low confidence for everything
        return {
            "medication_name": _extract_line(raw_text, 0),
            "medication_name_confidence": 0.4,
            "dosage": _extract_line(raw_text, 1),
            "dosage_confidence": 0.4,
            "raw_text": raw_text,
        }
    except Exception as exc:
        logger.error("Tesseract OCR failed: %s", exc)
        return {"raw_text": "", "medication_name": None, "medication_name_confidence": 0.0}


def _extract_line(text: str, index: int) -> str | None:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[index] if index < len(lines) else None


def confirm_scan(
    db: Session,
    scan: PrescriptionScan,
    confirmed_by: int,
    field_corrections: dict[int, str] | None = None,
) -> PrescriptionScan:
    """Coordinator confirms a scan. Apply corrections, advance state, auto-populate meds."""
    if scan.status not in SCAN_VALID_TRANSITIONS or "confirmed" not in SCAN_VALID_TRANSITIONS.get(scan.status, set()):
        raise ValueError(f"Cannot confirm scan in status '{scan.status}'")

    if field_corrections:
        for field_id, corrected_value in field_corrections.items():
            field = db.query(ExtractedMedicationField).filter(
                ExtractedMedicationField.id == field_id,
                ExtractedMedicationField.scan_id == scan.id,
            ).first()
            if field:
                field.is_corrected = True
                field.corrected_value = corrected_value

    scan.status = "confirmed"
    scan.confirmed_by = confirmed_by
    scan.confirmed_at = datetime.utcnow()
    db.commit()

    _auto_populate_medication(db, scan)
    return scan


def reject_scan(db: Session, scan: PrescriptionScan) -> PrescriptionScan:
    if "rejected" not in SCAN_VALID_TRANSITIONS.get(scan.status, set()):
        raise ValueError(f"Cannot reject scan in status '{scan.status}'")
    scan.status = "rejected"
    db.commit()
    db.refresh(scan)
    return scan


def _auto_populate_medication(db: Session, scan: PrescriptionScan) -> None:
    """Create Medication, PatientMedication, DispensingRecord from confirmed scan."""
    fields = {f.field_name: (f.corrected_value if f.is_corrected else f.extracted_value)
              for f in scan.fields}

    med_name = fields.get("medication_name")
    if not med_name:
        return

    generic = fields.get("generic_name") or med_name
    medication = db.query(Medication).filter(Medication.generic_name == generic).first()
    if not medication:
        medication = Medication(
            name=med_name,
            generic_name=generic,
            default_refill_days=int(fields.get("refill_days") or 30),
        )
        db.add(medication)
        db.flush()

    pm = db.query(PatientMedication).filter(
        PatientMedication.patient_id == scan.patient_id,
        PatientMedication.medication_id == medication.id,
        PatientMedication.is_active == True,
    ).first()
    if not pm:
        pm = PatientMedication(
            patient_id=scan.patient_id,
            medication_id=medication.id,
            dosage=fields.get("dosage"),
            refill_interval_days=int(fields["refill_days"]) if fields.get("refill_days") else medication.default_refill_days,
            is_active=True,
        )
        db.add(pm)

    dispense_date_str = fields.get("dispense_date")
    if dispense_date_str:
        try:
            dispense_date = datetime.strptime(dispense_date_str, "%Y-%m-%d")
            days_supply = int(fields.get("refill_days") or medication.default_refill_days)
            record = DispensingRecord(
                patient_id=scan.patient_id,
                medication_id=medication.id,
                dispensed_at=dispense_date,
                days_supply=days_supply,
                source="ocr",
            )
            db.add(record)
        except ValueError:
            logger.warning("Could not parse dispense_date '%s' for scan %s", dispense_date_str, scan.id)

    db.commit()

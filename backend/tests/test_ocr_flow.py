"""
T-49: Integration tests - prescription OCR flow.
upload -> extract -> review -> confirm -> medication populated
"""
import io
from unittest.mock import patch
import pytest


class TestOcrFlow:
    @patch("app.services.ocr_service._gpt4o_ocr")
    def test_prescription_upload(self, mock_gpt, client, auth_headers, db, test_patient, test_medication):
        """Upload a prescription image - scan record created."""
        mock_gpt.return_value = {
            "medication_name": "Metformin",
            "medication_name_confidence": 0.95,
            "dosage": "500mg",
            "dosage_confidence": 0.88,
        }
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        resp = client.post(
            f"/api/prescriptions?patient_id={test_patient.id}",
            files={"file": ("test.png", io.BytesIO(image_bytes), "image/png")},
            headers=auth_headers,
        )
        assert resp.status_code in (200, 201), resp.text
        data = resp.json()
        assert data["patient_id"] == test_patient.id
        assert data["status"] in ("review", "pending_review", "processing", "confirmed", "pending")

    def test_prescription_confirm(self, client, auth_headers, db, test_patient):
        """Confirming a scan should advance status to confirmed."""
        from app.models.models import PrescriptionScan, ExtractedMedicationField

        scan = PrescriptionScan(
            patient_id=test_patient.id,
            image_path="/tmp/test_scan_c.png",
            image_hash="abc123def456confirm01",
            source="telegram",
            ocr_engine="gpt4o",
            status="review",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        field = ExtractedMedicationField(
            scan_id=scan.id,
            field_name="medication_name",
            extracted_value="Metformin",
            confidence=0.92,
        )
        db.add(field)
        db.commit()

        resp = client.patch(
            f"/api/prescriptions/{scan.id}/confirm",
            json={"field_overrides": []},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "confirmed"

    def test_prescription_reject(self, client, auth_headers, db, test_patient):
        """Rejecting a scan should set status to rejected."""
        from app.models.models import PrescriptionScan

        scan = PrescriptionScan(
            patient_id=test_patient.id,
            image_path="/tmp/test_scan_r.png",
            image_hash="rejecthash9990001xx",
            source="telegram",
            ocr_engine="gpt4o",
            status="review",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        resp = client.patch(
            f"/api/prescriptions/{scan.id}/reject",
            json={"reason": "image_unreadable"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "rejected"

    def test_prescription_list(self, client, auth_headers):
        """GET /api/prescriptions returns a list."""
        resp = client.get("/api/prescriptions", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        assert isinstance(items, list)

    def test_image_path_not_in_response(self, client, auth_headers, db, test_patient):
        """image_path must never appear in the API response."""
        from app.models.models import PrescriptionScan

        scan = PrescriptionScan(
            patient_id=test_patient.id,
            image_path="/sensitive/path/scan_pii.png",
            image_hash="sensitivetest001xxxx",
            source="coordinator_upload",
            ocr_engine="tesseract",
            status="pending",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        resp = client.get(f"/api/prescriptions/{scan.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert "/sensitive/path/scan_pii.png" not in resp.text, "image_path leaked"
        assert "image_path" not in resp.json(), "image_path key present in response"

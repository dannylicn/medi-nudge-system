"""
Tests for S3 image storage paths in ocr_service and prescriptions router.
Covers: S3 upload, local fallback, pre-signed URL generation, and image serve endpoint.
"""
import io
from unittest.mock import MagicMock, patch

import pytest


class TestS3StorageUpload:
    """T4: ocr_service._store_image_s3 called when AWS_S3_BUCKET_NAME is set."""

    @patch("app.services.ocr_service._gpt4o_ocr")
    @patch("app.services.ocr_service.boto3")
    def test_upload_uses_s3_when_bucket_configured(
        self, mock_boto3, mock_gpt, client, auth_headers, db, test_patient, monkeypatch
    ):
        monkeypatch.setattr("app.services.ocr_service.settings.AWS_S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setattr("app.services.ocr_service.settings.AWS_REGION", "ap-southeast-1")

        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client
        # generate_image_url also calls boto3.client for the presigned URL
        mock_s3_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/prescriptions/1/img.jpg?sig=x"
        )
        mock_gpt.return_value = {"medication_name": "Metformin", "medication_name_confidence": 0.9}

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        resp = client.post(
            f"/api/prescriptions?patient_id={test_patient.id}",
            files={"file": ("rx.png", io.BytesIO(image_bytes), "image/png")},
            headers=auth_headers,
        )

        assert resp.status_code in (200, 201), resp.text
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"].startswith("prescriptions/")
        assert call_kwargs["ServerSideEncryption"] == "aws:kms"

        # image_path stored as S3 object key (not absolute path)
        from app.models.models import PrescriptionScan
        scan = db.query(PrescriptionScan).filter(
            PrescriptionScan.patient_id == test_patient.id
        ).first()
        assert scan is not None
        assert not scan.image_path.startswith("/")

    @patch("app.services.ocr_service._gpt4o_ocr")
    def test_upload_uses_local_when_no_bucket(
        self, mock_gpt, client, auth_headers, db, test_patient, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("app.services.ocr_service.settings.AWS_S3_BUCKET_NAME", "")
        monkeypatch.setattr(
            "app.services.ocr_service.settings.MEDIA_STORAGE_PATH", str(tmp_path)
        )

        mock_gpt.return_value = {"medication_name": "Amlodipine", "medication_name_confidence": 0.85}

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        resp = client.post(
            f"/api/prescriptions?patient_id={test_patient.id}",
            files={"file": ("rx2.png", io.BytesIO(image_bytes), "image/png")},
            headers=auth_headers,
        )

        assert resp.status_code in (200, 201), resp.text
        from app.models.models import PrescriptionScan
        scan = db.query(PrescriptionScan).filter(
            PrescriptionScan.patient_id == test_patient.id
        ).first()
        assert scan is not None
        assert scan.image_path.startswith(str(tmp_path))


class TestPresignedUrls:
    """T5: generate_image_url returns pre-signed URL when S3 is configured."""

    @patch("app.services.ocr_service.boto3")
    def test_generate_image_url_returns_presigned_url(self, mock_boto3, monkeypatch):
        from app.models.models import PrescriptionScan
        from app.services.ocr_service import generate_image_url

        monkeypatch.setattr("app.services.ocr_service.settings.AWS_S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setattr("app.services.ocr_service.settings.AWS_REGION", "ap-southeast-1")

        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/prescriptions/1/abc_123.jpg?X-Amz-Signature=sig"
        )
        mock_boto3.client.return_value = mock_s3_client

        scan = PrescriptionScan()
        scan.id = 1
        # Relative (S3 key) path
        scan.image_path = "prescriptions/1/abc_123.jpg"

        url = generate_image_url(scan, "https://api.example.com")

        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "prescriptions/1/abc_123.jpg"},
            ExpiresIn=900,
        )
        assert "X-Amz-Signature" in url

    def test_generate_image_url_returns_local_url_when_no_bucket(self, monkeypatch):
        from app.models.models import PrescriptionScan
        from app.services.ocr_service import generate_image_url

        monkeypatch.setattr("app.services.ocr_service.settings.AWS_S3_BUCKET_NAME", "")

        scan = PrescriptionScan()
        scan.id = 42
        scan.image_path = "/tmp/media/prescriptions/42/abc.jpg"

        url = generate_image_url(scan, "http://localhost:8000")
        assert url == "http://localhost:8000/api/prescriptions/42/image"


class TestImageServeEndpoint:
    """/{scan_id}/image redirects to pre-signed URL in S3 mode; serves bytes in local mode."""

    @patch("app.routers.prescriptions.boto3")
    def test_image_endpoint_redirects_to_s3_presigned_url(
        self, mock_boto3, client, auth_headers, db, test_patient, monkeypatch
    ):
        from app.models.models import PrescriptionScan
        from app.core.config import settings as app_settings

        monkeypatch.setattr(app_settings, "AWS_S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setattr(app_settings, "AWS_REGION", "ap-southeast-1")

        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/prescriptions/1/img.jpg?sig=abc"
        )
        mock_boto3.client.return_value = mock_s3_client

        scan = PrescriptionScan(
            patient_id=test_patient.id,
            image_path="prescriptions/1/img.jpg",  # relative — S3 key
            image_hash="s3redirecttest001",
            source="web_upload",
            status="review",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        resp = client.get(
            f"/api/prescriptions/{scan.id}/image",
            headers=auth_headers,
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "s3.amazonaws.com" in resp.headers["location"]

    def test_image_endpoint_serves_bytes_locally(
        self, client, auth_headers, db, test_patient, tmp_path, monkeypatch
    ):
        from app.models.models import PrescriptionScan
        from app.core.config import settings as app_settings

        monkeypatch.setattr(app_settings, "AWS_S3_BUCKET_NAME", "")

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)

        scan = PrescriptionScan(
            patient_id=test_patient.id,
            image_path=str(img_file),
            image_hash="localservetest0001",
            source="web_upload",
            status="review",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        resp = client.get(
            f"/api/prescriptions/{scan.id}/image",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"



class TestS3StorageUpload:
    """T4: ocr_service._store_image_s3 called when AWS_S3_BUCKET_NAME is set."""

    @patch("app.services.ocr_service._gpt4o_ocr")
    @patch("app.services.ocr_service.boto3")
    def test_upload_uses_s3_when_bucket_configured(
        self, mock_boto3, mock_gpt, client, auth_headers, db, test_patient, monkeypatch
    ):
        monkeypatch.setattr("app.services.ocr_service.settings.AWS_S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setattr("app.services.ocr_service.settings.AWS_REGION", "ap-southeast-1")

        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client
        mock_gpt.return_value = {"medication_name": "Metformin", "medication_name_confidence": 0.9}

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        resp = client.post(
            f"/api/prescriptions?patient_id={test_patient.id}",
            files={"file": ("rx.png", io.BytesIO(image_bytes), "image/png")},
            headers=auth_headers,
        )

        assert resp.status_code in (200, 201), resp.text
        mock_boto3.client.assert_called_with("s3", region_name="ap-southeast-1")
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"].startswith("prescriptions/")
        assert call_kwargs["ServerSideEncryption"] == "aws:kms"

        # image_path stored as S3 object key (not absolute path)
        from app.models.models import PrescriptionScan
        scan = db.query(PrescriptionScan).filter(
            PrescriptionScan.patient_id == test_patient.id
        ).first()
        assert scan is not None
        assert not scan.image_path.startswith("/")

    @patch("app.services.ocr_service._gpt4o_ocr")
    def test_upload_uses_local_when_no_bucket(
        self, mock_gpt, client, auth_headers, db, test_patient, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("app.services.ocr_service.settings.AWS_S3_BUCKET_NAME", "")
        monkeypatch.setattr(
            "app.services.ocr_service.settings.MEDIA_STORAGE_PATH", str(tmp_path)
        )

        mock_gpt.return_value = {"medication_name": "Amlodipine", "medication_name_confidence": 0.85}

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        resp = client.post(
            f"/api/prescriptions?patient_id={test_patient.id}",
            files={"file": ("rx2.png", io.BytesIO(image_bytes), "image/png")},
            headers=auth_headers,
        )

        assert resp.status_code in (200, 201), resp.text
        from app.models.models import PrescriptionScan
        scan = db.query(PrescriptionScan).filter(
            PrescriptionScan.patient_id == test_patient.id
        ).first()
        assert scan is not None
        assert scan.image_path.startswith(str(tmp_path))


class TestPresignedUrls:
    """T5: generate_image_url returns pre-signed URL when S3 is configured."""

    @patch("app.services.ocr_service.boto3")
    def test_generate_image_url_returns_presigned_url(self, mock_boto3, monkeypatch):
        from app.models.models import PrescriptionScan
        from app.services.ocr_service import generate_image_url

        monkeypatch.setattr("app.services.ocr_service.settings.AWS_S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setattr("app.services.ocr_service.settings.AWS_REGION", "ap-southeast-1")

        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/prescriptions/1/abc_123.jpg?X-Amz-Signature=sig"
        )
        mock_boto3.client.return_value = mock_s3_client

        scan = PrescriptionScan()
        scan.id = 1
        # Relative (S3 key) path
        scan.image_path = "prescriptions/1/abc_123.jpg"

        url = generate_image_url(scan, "https://api.example.com")

        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "prescriptions/1/abc_123.jpg"},
            ExpiresIn=900,
        )
        assert "X-Amz-Signature" in url

    def test_generate_image_url_returns_local_url_when_no_bucket(self, monkeypatch):
        from app.models.models import PrescriptionScan
        from app.services.ocr_service import generate_image_url

        monkeypatch.setattr("app.services.ocr_service.settings.AWS_S3_BUCKET_NAME", "")

        scan = PrescriptionScan()
        scan.id = 42
        scan.image_path = "/tmp/media/prescriptions/42/abc.jpg"

        url = generate_image_url(scan, "http://localhost:8000")
        assert url == "http://localhost:8000/api/prescriptions/42/image"


class TestImageServeEndpoint:
    """/{scan_id}/image redirects to pre-signed URL in S3 mode; serves bytes in local mode."""

    @patch("app.routers.prescriptions.boto3")
    def test_image_endpoint_redirects_to_s3_presigned_url(
        self, mock_boto3, client, auth_headers, db, test_patient, monkeypatch
    ):
        from app.models.models import PrescriptionScan
        from app.core.config import settings as app_settings

        monkeypatch.setattr(app_settings, "AWS_S3_BUCKET_NAME", "test-bucket")
        monkeypatch.setattr(app_settings, "AWS_REGION", "ap-southeast-1")

        mock_s3_client = MagicMock()
        mock_s3_client.generate_presigned_url.return_value = (
            "https://test-bucket.s3.amazonaws.com/prescriptions/1/img.jpg?sig=abc"
        )
        mock_boto3.client.return_value = mock_s3_client

        scan = PrescriptionScan(
            patient_id=test_patient.id,
            image_path="prescriptions/1/img.jpg",  # relative — S3 key
            image_hash="s3redirecttest001",
            source="web_upload",
            status="review",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        resp = client.get(
            f"/api/prescriptions/{scan.id}/image",
            headers=auth_headers,
            follow_redirects=False,
        )
        assert resp.status_code == 302
        assert "s3.amazonaws.com" in resp.headers["location"]

    def test_image_endpoint_serves_bytes_locally(
        self, client, auth_headers, db, test_patient, tmp_path, monkeypatch
    ):
        from app.models.models import PrescriptionScan
        from app.core.config import settings as app_settings

        monkeypatch.setattr(app_settings, "AWS_S3_BUCKET_NAME", "")

        img_file = tmp_path / "test.jpg"
        img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 50)

        scan = PrescriptionScan(
            patient_id=test_patient.id,
            image_path=str(img_file),
            image_hash="localservetest0001",
            source="web_upload",
            status="review",
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)

        resp = client.get(
            f"/api/prescriptions/{scan.id}/image",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/jpeg"

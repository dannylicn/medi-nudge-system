"""Pydantic schemas for all API request/response models."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator
import re


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def validate_e164(phone: str) -> str:
    """Normalise and validate E.164 phone numbers."""
    # Strip all whitespace and common separators
    phone = re.sub(r"[\s\-\.\(\)]", "", phone.strip())
    # Allow bare 8-digit Singapore numbers and auto-prefix
    if re.match(r"^[89]\d{7}$", phone):
        phone = "+65" + phone
    if not re.match(r"^\+\d{7,15}$", phone):
        raise ValueError("Phone number must be in E.164 format, e.g. +6591234567")
    return phone


SUPPORTED_LANGUAGES = {"en", "zh", "ms", "ta"}
SUPPORTED_RISK_LEVELS = {"low", "normal", "high"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Patient
# ---------------------------------------------------------------------------

class PatientCreate(BaseModel):
    full_name: str
    phone_number: str
    nric: str  # Plaintext NRIC/FIN — hashed before storage, never persisted
    age: Optional[int] = None
    language_preference: str = "en"
    conditions: list[str] = []
    risk_level: str = "normal"
    caregiver_name: Optional[str] = None
    caregiver_phone_number: Optional[str] = None  # E.164 — Twilio sends invite link here

    @field_validator("caregiver_phone_number")
    @classmethod
    def normalise_caregiver_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v.strip() == "":
            return None
        return validate_e164(v.strip())

    @field_validator("nric")
    @classmethod
    def validate_nric(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[STFGM]\d{7}[A-Z]$", v):
            raise ValueError("NRIC/FIN must be in format S1234567A (S/T/F/G/M + 7 digits + letter)")
        return v

    @field_validator("phone_number")
    @classmethod
    def normalise_phone(cls, v: str) -> str:
        v = v.strip()
        # Accept Telegram chat_id (numeric string)
        if re.match(r"^\d{5,15}$", v):
            return v
        return validate_e164(v)

    @field_validator("language_preference")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"language_preference must be one of {SUPPORTED_LANGUAGES}")
        return v

    @field_validator("risk_level")
    @classmethod
    def validate_risk(cls, v: str) -> str:
        if v not in SUPPORTED_RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {SUPPORTED_RISK_LEVELS}")
        return v


class PatientUpdate(BaseModel):
    full_name: Optional[str] = None
    age: Optional[int] = None
    language_preference: Optional[str] = None
    conditions: Optional[list[str]] = None
    risk_level: Optional[str] = None
    is_active: Optional[bool] = None
    contact_window_start: Optional[str] = None
    contact_window_end: Optional[str] = None
    caregiver_name: Optional[str] = None
    caregiver_phone_number: Optional[str] = None  # E.164 — triggers invite SMS when set
    caregiver_telegram_id: Optional[str] = None   # auto-populated once caregiver links bot
    nudge_delivery_mode: Optional[str] = None
    selected_voice_id: Optional[str] = None

    @field_validator("language_preference")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"language_preference must be one of {SUPPORTED_LANGUAGES}")
        return v

    @field_validator("risk_level")
    @classmethod
    def validate_risk(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SUPPORTED_RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {SUPPORTED_RISK_LEVELS}")
        return v


class PatientOut(BaseModel):
    id: int
    full_name: str
    phone_number: str
    age: Optional[int]
    language_preference: str
    conditions: list
    risk_level: str
    is_active: bool
    onboarding_state: str
    consent_obtained_at: Optional[datetime]
    contact_window_start: Optional[str]
    contact_window_end: Optional[str]
    caregiver_name: Optional[str]
    caregiver_phone_number: Optional[str]
    caregiver_telegram_id: Optional[str]
    telegram_chat_id: Optional[str]
    nudge_delivery_mode: str = "text"
    selected_voice_id: Optional[str] = None
    created_at: datetime
    # Populated only on creation / token regeneration, not stored on the model
    invite_link: Optional[str] = None
    onboarding_qr_code: Optional[str] = None  # base64 PNG
    # nric_hash is intentionally excluded from API responses

    class Config:
        from_attributes = True


class PatientListResponse(BaseModel):
    items: list[PatientOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Medication
# ---------------------------------------------------------------------------

class MedicationCreate(BaseModel):
    name: str
    generic_name: str
    category: Optional[str] = None
    default_refill_days: int = 30


class MedicationOut(BaseModel):
    id: int
    name: str
    generic_name: str
    category: Optional[str]
    default_refill_days: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# PatientMedication
# ---------------------------------------------------------------------------

class PatientMedicationCreate(BaseModel):
    medication_id: int
    dosage: Optional[str] = None
    refill_interval_days: Optional[int] = None
    frequency: str = "once_daily"
    reminder_times: Optional[list[str]] = None  # ["08:00"] or ["08:00", "20:00"] SGT


class PatientMedicationOut(BaseModel):
    id: int
    patient_id: int
    medication_id: int
    dosage: Optional[str]
    refill_interval_days: Optional[int]
    frequency: str
    reminder_times: Optional[list[str]]
    consecutive_missed_doses: int
    last_reminded_at: Optional[datetime]
    last_taken_at: Optional[datetime]
    is_active: bool
    medication: Optional[MedicationOut] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# DispensingRecord
# ---------------------------------------------------------------------------

class DispensingRecordCreate(BaseModel):
    patient_id: int
    medication_id: int
    dispensed_at: datetime
    days_supply: int
    quantity: Optional[int] = None
    source: str = "manual"


class DispensingRecordOut(BaseModel):
    id: int
    patient_id: int
    medication_id: int
    dispensed_at: datetime
    days_supply: int
    quantity: Optional[int]
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Condition & condition-medication mapping
# ---------------------------------------------------------------------------

class ConditionOut(BaseModel):
    id: int
    name: str
    medications: list[MedicationOut] = []

    class Config:
        from_attributes = True


class ConditionCreate(BaseModel):
    name: str


class ConditionMedicationAdd(BaseModel):
    medication_id: int


# ---------------------------------------------------------------------------
# NudgeCampaign
# ---------------------------------------------------------------------------

class NudgeCampaignOut(BaseModel):
    id: int
    patient_id: int
    medication_id: int
    status: str
    days_overdue: int
    attempt_number: int
    message_content: Optional[str]
    language: str
    response: Optional[str]
    response_type: Optional[str]
    created_at: datetime
    last_sent_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# EscalationCase
# ---------------------------------------------------------------------------

class EscalationCaseOut(BaseModel):
    id: int
    nudge_campaign_id: Optional[int]
    patient_id: int
    reason: str
    priority: str
    status: str
    assigned_to: Optional[str]
    notes: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EscalationCaseUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# PrescriptionScan
# ---------------------------------------------------------------------------

class ExtractedFieldOut(BaseModel):
    id: int
    field_name: str
    extracted_value: Optional[str]
    confidence: float
    is_corrected: bool
    corrected_value: Optional[str]

    class Config:
        from_attributes = True


class ExtractedFieldUpdate(BaseModel):
    corrected_value: str


class PrescriptionScanOut(BaseModel):
    id: int
    patient_id: int
    image_url: Optional[str] = None   # Signed URL, not raw path
    source: str
    ocr_engine: Optional[str]
    status: str
    confirmed_by: Optional[int]
    confirmed_at: Optional[datetime]
    uploaded_at: datetime
    fields: list[ExtractedFieldOut] = []
    # image_path intentionally excluded

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# DoseLog
# ---------------------------------------------------------------------------

class DoseLogOut(BaseModel):
    id: int
    patient_id: int
    medication_id: int
    status: str
    source: str
    logged_at: datetime
    created_at: datetime
    medication_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# OutboundMessage
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# VoiceProfile
# ---------------------------------------------------------------------------

class VoiceProfileOut(BaseModel):
    id: int
    patient_id: int
    donor_name: Optional[str]
    elevenlabs_voice_id: Optional[str]
    patient_consent_at: Optional[datetime]
    donor_consent_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# OutboundMessage
# ---------------------------------------------------------------------------

class OutboundMessageOut(BaseModel):
    id: int
    campaign_id: Optional[int]
    patient_id: int
    content: Optional[str]
    delivery_mode: str
    status: str
    sent_at: datetime
    delivered_at: Optional[datetime]

    class Config:
        from_attributes = True

# Medi-Nudge System

A personalised medication adherence platform for chronic disease patients, using WhatsApp nudges, prescription OCR, escalation workflows, and a care coordinator dashboard.

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for prescription scanning)

---

## Backend (FastAPI)

### 1. Set up a virtual environment

```bash
cd backend
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the `backend/` directory:

```env
DATABASE_URL=sqlite:///./medi_nudge.db
JWT_SECRET_KEY=your-secret-key-here

# Optional — required for WhatsApp messaging
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# Optional — required for AI nudge generation
OPENAI_API_KEY=

MEDIA_STORAGE_PATH=./media
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the development server

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**  
Interactive docs: **http://localhost:8000/docs**

---

## Frontend (React + Vite)

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. Start the development server

```bash
npm run dev
```

The app will be available at **http://localhost:5173**

---

## Running Tests

From the `backend/` directory (with the virtual environment activated):

```bash
pytest
```

To run with coverage:

```bash
pytest --cov=app
```

---

## Project Structure

```
medi-nudge-system/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── core/         # Config, database, scheduler, security
│   │   ├── models/       # SQLAlchemy models
│   │   ├── routers/      # API route handlers
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic (nudges, OCR, escalations, WhatsApp)
│   ├── migrations/       # Alembic DB migrations
│   ├── tests/            # Pytest test suite
│   └── requirements.txt
├── frontend/             # React + Vite frontend
│   └── src/
│       ├── components/   # Shared UI components
│       ├── pages/        # Route-level page components
│       ├── hooks/        # Custom React hooks
│       └── lib/          # API client
└── docs/                 # Additional documentation
```

---

## Key Features

- **WhatsApp nudges** — scheduled medication reminders via Twilio
- **Prescription OCR** — extract medication data from uploaded images
- **Escalation engine** — flags non-adherent patients for care coordinator follow-up
- **Analytics dashboard** — adherence trends and patient insights
- **Caregiver loop** — loop in caregivers when patient is unresponsive

# Floor Price Validator

Streamlit-based suite for checking broadband floor prices, capturing audit logs, and exposing a public verification portal.

## Project layout

| Path | Description |
| --- | --- |
| `app.py` | Internal app for price checks, history, document lookup, admin tools |
| `verify_app.py` | Public verification endpoint served at `/verify/<reference_id>` |
| `database.py` | SQLAlchemy models and helpers (users, OTP, price checks, configs) |
| `floor_price.py` | Pricing and margin calculation engine |
| `document_export.py` | HTML/TXT document generators for audit outputs |
| `config.py` | Default pricing configuration used when no DB override exists |

## Requirements

- Python 3.10+
- SQLite (bundled)
- Virtual environment recommended (`python -m venv venv`)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Environment configuration (`.env`)

Create a `.env` file in the project root to supply runtime variables consumed by `config.py` and other modules.

```env
# Authentication domain and admin list
ALLOWED_EMAIL_DOMAIN=ntplc.co.th
ADMIN_EMAILS=admin@ntplc.co.th,supervisor@ntplc.co.th

# SMTP settings (set DEV_MODE=false to enable real email)
DEV_MODE=true
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=mailer@example.com
SMTP_PASSWORD=change-me
FROM_EMAIL=noreply@example.com
SENDER_NAME="Floor Price Validator"

# Database + security
DATABASE_URL=sqlite:///floor_price.db
SECRET_KEY=replace-with-random-string
OTP_EXPIRY_MINUTES=5
```

Adjust values for production (e.g., `DEV_MODE=false`, real SMTP credentials, secure `SECRET_KEY`).

## Optional secrets (`.streamlit/secrets.toml`)

If you prefer to keep certain values outside `.env`, create `.streamlit/secrets.toml`:

```toml
MAIN_APP_URL = "https://floorprice.example.com"
```

`verify_app.py` will read `MAIN_APP_URL` from secrets first, then fall back to the `MAIN_APP_URL` environment variable if present.

## Database preparation

Ensure the SQLite schema is up to date (creates/extends tables in place):

```bash
python -c "import database; print('schema ensured')"
```

## Running the applications

### Internal validator (authenticated users)

```bash
streamlit run app.py
```

Provides tabs for price checks, document verification, comparison tables, history, and admin dashboards.

### Public verification portal

```bash
streamlit run verify_app.py
```

Accessible at `/verify/<reference_id>` after deployment (JavaScript shim rewrites friendly URLs to Streamlit query parameters). Includes a link back to the main app when `MAIN_APP_URL` is defined.

## Testing

Run the existing test suite after installation:

```bash
pytest
```

Add more tests under `test/` as needed.

## Deployment notes

- Configure `.env` or environment variables with production-ready SMTP, database, and security values.
- Provide `MAIN_APP_URL` (via secrets or env) to enable navigation back to the internal system from the verification portal.
- Behind a reverse proxy, route `/verify/*` to `verify_app.py` and the rest to the internal app, applying authentication only where appropriate.

## Document verification flow

1. Internal users run checks via `app.py`; each run generates a `reference_id` and optional HTML/TXT exports.
2. Auditors browse `https://floorprice.example.com/verify/<reference_id>` (served by `verify_app.py`) to confirm stored results or download the documents again.

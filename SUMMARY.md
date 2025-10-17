# 📦 Floor Price Validator v2.0 – Summary (Current)

## 1. Core Modules

| File | Purpose | Key Functions/Notes |
| --- | --- | --- |
| `config.py` | Default pricing tables, equipment SKUs, installation rules, contract discounts, fixed IP pricing | Matches `floor_price_plan.md`; used when no DB override |
| `config_manager.py` | SQLAlchemy model + helpers for `pricing_configs` | `get_active_config`, `create_default_config`, `duplicate_config`; installation columns represent base cost/length + extra cost per meter |
| `floor_price.py` | Pricing engine | Calculates floor (existing/new/weighted), net revenue (after discount + 4% regulator fee), margin (baht/% using net revenue as denominator), comparison table data |
| `database.py` | ORM models & persistence utilities | `ensure_price_checks_schema`, `log_price_check_comprehensive`, `get_user_logs`, `mark_as_exported`, `get_price_check_by_reference`; `price_checks` table stores floor/margin/export metadata |
| `document_export.py` | Builds HTML/TXT outputs | `generate_verification_document_html`, `generate_simple_summary_text`, currency formatting helpers |
| `auth.py` | OTP & user management | Email OTP delivery, domain checks, admin toggles |

## 2. Streamlit Application (`app.py`)

- **"✅ ตรวจสอบราคา"** – captures package details, discount, customer mix ⇒ computes floor (existing/new/weighted), net revenue, margin (บาท/%) and stores log with Reference ID; offers HTML/TXT export and export tracking.
- **"🔍 ตรวจสอบเอกสาร"** – lookup by Reference ID, display full log, allow re-export.
- **"📈 ตารางเปรียบเทียบ"** – generates dataframe + Plotly chart for all bandwidth tiers; CSV export supported; Plotly rendered with `config={'responsive': True}`.
- **"📊 ประวัติของฉัน"** – shows current user’s checks, including margin results and export metadata.
- **"🔧 Admin Dashboard"** – manage users, inspect statistics/logs, adjust pricing configs (activating overrides stored in DB).

Implementation notes:
- All Streamlit buttons have explicit `key` values to avoid duplicate IDs.
- Margin percent everywhere uses net revenue as denominator, consistent with business rules.
- Equipment multiselect uses SKU labels from `Config.EQUIPMENT_PRICES`.

## 3. Database Snapshot

### `price_checks`
- Stores pricing inputs (speed, distance km, equipment list, contract months, discount %, proposed price, fixed IP flag, customer ratios) and outputs (floor_existing/new/weighted, margin_* baht/percent, net_revenue, regulator_fee, validity flags).
- Tracks export data (`reference_id`, `exported_by`, `exported_at`, `export_count`) plus notes.
- `ensure_price_checks_schema()` adds missing columns on import so legacy DBs migrate in place.

### `pricing_configs`
- Holds override tables for speeds, equipment, installation, discounts, fixed IP, business premium.
- Admin UI selects the active config; falling back to `config.py` when none active.

## 4. Supporting Scripts

| Script | Description |
| --- | --- |
| `migrate_to_v2.py` | Validates required files, backs up key modules, checks dependencies, ensures DB schema, and runs sample calculations using current equipment set |
| `init_config.py` | Seeds default pricing config into DB |
| `migrate_db.py` / `migrate_db_v2.py` | Historical migration helpers retained for reference |
| `fix_json_keys.py` | Utility for normalising config JSON key formats |

## 5. Typical Workflow

1. **Price check** → user fills form on "✅ ตรวจสอบราคา" → system logs result, shows floor/margin, generates Reference ID → export documents if needed.
2. **Document verification** → stakeholder enters Reference ID → system displays stored calculation and permits re-export.
3. **Pricing analysis** → team uses "📈 ตารางเปรียบเทียบ" to review floor pricing across bandwidths, adjust mixes/discounts, download CSV.
4. **Admin maintenance** → admins manage users, review activity logs, and publish updated pricing configs.

## 6. Setup & Testing

1. Create virtualenv and install `requirements.txt` (Streamlit, SQLAlchemy, pandas, plotly, qrcode[pil], reportlab, etc.).
2. Run `python -c "import database; print('schema ensured')"` to auto-migrate the SQLite schema.
3. (Optional) Execute `python migrate_to_v2.py` for environment validation and sample calculation checks.
4. Launch with `streamlit run app.py`.
5. Run `pytest` (currently includes OTP test) and add additional tests where necessary.

## 7. Documentation Set

- `README_v2.md` – comprehensive manual (calculations, setup, troubleshooting).
- `QUICKSTART.md` – fast-start guide for Product/Marketing/Sales teams with real scenarios and tips.
- `price_calculate.md` – step-by-step formula breakdown with numerical examples.

## 8. Roadmap Highlights

- PDF export (Thai font support), automated email delivery, digital signature integration.
- QR-code verification endpoint.
- Expanded analytics dashboard for margin/pass-rate trends.

---
_Last updated to reflect repository state on branch `main` after v2.0 refactor._

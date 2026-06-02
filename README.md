# api-automation-tests

Python API test suite for the SalarySe BBPS (Bharat Bill Payment System) service.
Uses **pytest + requests** against the live dev gateway at `https://api.dev.salaryse.com`.

---

## Project structure

```
api-automation-tests/
├── config/
│   └── settings.py          # All env-var loading in one place
├── utils/
│   └── api_client.py        # SalarySeClient (HTTP) + ApiResponse (assertions)
├── tests/
│   └── bbps/
│       ├── conftest.py      # Session-scoped shared fixtures (login, account, bill, order)
│       ├── test_discovery.py    # Categories → Billers → Biller details
│       ├── test_bill_fetch.py   # Validate account → Fetch bill
│       ├── test_order.py        # Estimate → Create order → Get → History → Receipt
│       ├── test_prepaid.py      # Operators → Circles → Plans → Plan by ID
│       ├── test_bill_actions.py # Mark paid · Deactivate account · Dashboard · CUB biller
│       └── test_negative.py     # Auth failures · Invalid inputs · Error envelope structure
├── conftest.py              # Session-scoped client fixture (login once)
├── pytest.ini
├── requirements.txt
└── .env.example
```

---

## Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/avinash-salaryse/api-automation-tests.git
cd api-automation-tests

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum set TEST_PHONE, TEST_BILLER_CATEGORY_REF_ID,
# TEST_BILLER_REF_ID, TEST_CUSTOMER_PARAMS, and TEST_PREPAID_MOBILE
```

---

## .env reference

| Variable | Required | Description |
|---|---|---|
| `BASE_URL` | No | Gateway base URL (defaults to `https://api.dev.salaryse.com`) |
| `TEST_PHONE` | **Yes** | Phone number of the dev test user |
| `TEST_OTP` | No | Dev fixed OTP (defaults to `123456`) |
| `TEST_DEVICE_ID` | No | Device ID header (defaults to `test-automation-device-001`) |
| `TEST_APP_VERSION` | No | App version header (defaults to `3.5.0`) |
| `TEST_OS` | No | OS header — `android` or `ios` (defaults to `android`) |
| `TEST_BILLER_CATEGORY_REF_ID` | **Yes** | UUID of a biller category in the dev DB |
| `TEST_BILLER_REF_ID` | **Yes** | UUID of a biller in that category |
| `TEST_CUSTOMER_PARAMS` | **Yes** | JSON object of customer params for the above biller |
| `TEST_PREPAID_MOBILE` | Yes for prepaid | Mobile number for prepaid plan tests |
| `TEST_PREPAID_OPERATOR` | No | Operator code (skips auto-detection) |
| `TEST_PREPAID_CIRCLE_REF_ID` | No | Circle ref ID (skips auto-detection) |

### Finding test data (biller UUIDs)

Run the discovery tests first with just `TEST_PHONE` set — they will print the
category list and biller list. Pick UUIDs from that output and set them in `.env`.

---

## Running tests

```bash
# Full test run
pytest

# Smoke tests only (fast sanity check)
pytest -m smoke

# Specific flow
pytest tests/bbps/test_discovery.py
pytest tests/bbps/test_bill_fetch.py
pytest tests/bbps/test_order.py
pytest tests/bbps/test_prepaid.py

# Skip destructive tests (deactivate-account)
pytest -m "not destructive"

# Negative / error scenarios only
pytest -m negative

# Generate HTML report
pytest --html=report.html --self-contained-html
```

---

## Auth flow

1. `POST /gw/v1/login` — triggers OTP to the test phone
2. `POST /gw/v1/validate_otp` — validates OTP (fixed as `123456` in dev), returns `AuthToken`
3. The token is sent as the `x-token` header on every subsequent request

Login happens **once per test session** via the session-scoped `client` fixture in `conftest.py`.

---

## Fixture dependency chain

```
client (session)
  └── validated_account (session)  ← calls validate-account once
        └── fetched_bill (session) ← calls bill-fetch once
              └── created_order (session) ← calls create-order once
```

All API-calling fixtures are `scope="session"` — the gateway is hit once
and the results are shared across all tests in the run.

---

## Test markers

| Marker | Tests |
|---|---|
| `smoke` | Quick sanity: categories, validate-account, bill fetch, create order, operators |
| `discovery` | Biller categories + biller list + biller details |
| `bill_fetch` | validate-account + fetch-bill |
| `order` | Estimate, create, get, history, receipt, rewards |
| `prepaid` | Operators, circles, plans, plan-by-id |
| `bill_actions` | Mark-paid, deactivate-account, dashboard, CUB biller |
| `negative` | Auth failures, bad inputs, error envelope structure |
| `destructive` | Tests that change state (deactivate-account) — skip with `-m "not destructive"` |

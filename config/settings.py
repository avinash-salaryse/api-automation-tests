import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Server ────────────────────────────────────────────────────────────────────
BASE_URL: str = os.environ.get("BASE_URL", "https://api.dev.salaryse.com").rstrip("/")
ENV: str = os.environ.get("ENV", "dev").lower()  # allowed: dev, local

# ── Auth ──────────────────────────────────────────────────────────────────────
TEST_PHONE: str = os.environ.get("TEST_PHONE", "")
TEST_OTP: str = os.environ.get("TEST_OTP", "123456")

# ── Device headers ────────────────────────────────────────────────────────────
DEVICE_ID: str = os.environ.get("TEST_DEVICE_ID", "test-automation-device-001")
APP_VERSION: str = os.environ.get("TEST_APP_VERSION", "3.5.0")
OS: str = os.environ.get("TEST_OS", "android")

# ── BBPS test data ────────────────────────────────────────────────────────────
BILLER_CATEGORY_REF_ID: str = os.environ.get("TEST_BILLER_CATEGORY_REF_ID", "")
BILLER_REF_ID: str = os.environ.get("TEST_BILLER_REF_ID", "")
CUSTOMER_PARAMS: dict = json.loads(os.environ.get("TEST_CUSTOMER_PARAMS", "{}"))

# ── Prepaid test data ─────────────────────────────────────────────────────────
PREPAID_MOBILE: str = os.environ.get("TEST_PREPAID_MOBILE", "")
PREPAID_OPERATOR: str = os.environ.get("TEST_PREPAID_OPERATOR", "")
PREPAID_CIRCLE_REF_ID: str = os.environ.get("TEST_PREPAID_CIRCLE_REF_ID", "")

# ── UPI test data ─────────────────────────────────────────────────────────────
TEST_VPA: str = os.environ.get("TEST_UPI_VPA", "test@upi")

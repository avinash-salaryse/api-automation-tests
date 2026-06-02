"""
Session-scoped BBPS fixtures.

Each fixture that calls the API runs exactly once per test session and
caches the result. This means validate-account and bill-fetch are called
only once even when multiple test modules depend on them.
"""

import pytest

from config import settings


# ── Test-data fixtures (from env) ─────────────────────────────────────────────

@pytest.fixture(scope="session")
def biller_category_ref_id() -> str:
    if not settings.BILLER_CATEGORY_REF_ID:
        pytest.skip("TEST_BILLER_CATEGORY_REF_ID not set in .env")
    return settings.BILLER_CATEGORY_REF_ID


@pytest.fixture(scope="session")
def biller_ref_id() -> str:
    if not settings.BILLER_REF_ID:
        pytest.skip("TEST_BILLER_REF_ID not set in .env")
    return settings.BILLER_REF_ID


@pytest.fixture(scope="session")
def customer_params() -> dict:
    if not settings.CUSTOMER_PARAMS:
        pytest.skip("TEST_CUSTOMER_PARAMS not set in .env")
    return settings.CUSTOMER_PARAMS


@pytest.fixture(scope="session")
def prepaid_mobile() -> str:
    if not settings.PREPAID_MOBILE:
        pytest.skip("TEST_PREPAID_MOBILE not set in .env")
    return settings.PREPAID_MOBILE


# ── API-call fixtures (called once, result shared across all tests) ────────────

@pytest.fixture(scope="session")
def validated_account(client, biller_ref_id, customer_params) -> dict:
    """
    Calls POST /billers/{id}/validate-account once.
    Returns the full `data` dict from the response.
    Keys: accountReferenceId, customerParam, maxAmountAllowed,
          minAmountAllowed, allowsUpiCreditCard

    Some billers (e.g. PayU sandbox test billers) return
    VALIDATION_NOT_SUPPORTED_PREPAID — those tests are skipped.
    """
    resp = client.post(
        f"/gw/v1/bbps/billers/{biller_ref_id}/validate-account",
        payload={"customerParams": customer_params},
    )
    if resp.error_reason in (
        "VALIDATION_NOT_SUPPORTED_PREPAID",
        "ACCOUNT_VALIDATION_ERROR",
        "ACCOUNT_VALIDATION_FAILED",
    ):
        pytest.skip(
            f"Biller {biller_ref_id} does not support account validation "
            f"in this environment: {resp.error_reason}"
        )
    assert resp.ok, f"validate-account failed: {resp}"
    assert resp.data.get("accountReferenceId"), "No accountReferenceId in response"
    return resp.data


@pytest.fixture(scope="session")
def fetched_bill(client, biller_ref_id, customer_params) -> dict:
    """
    Calls POST /billers/{id}/bill once.
    Returns the full `data` dict from the response.
    Keys: billReferenceId, amount, dueDate, billDate, accountHolderName,
          minAmountDue, maxAmountAllowed, allowsUpiCreditCard
    """
    resp = client.post(
        f"/gw/v1/bbps/billers/{biller_ref_id}/bill",
        payload={"customerParams": customer_params},
    )
    assert resp.ok, f"bill fetch failed: {resp}"
    assert resp.data.get("billReferenceId"), "No billReferenceId in response"
    return resp.data


@pytest.fixture(scope="session")
def created_order(client, fetched_bill) -> dict:
    """
    Creates an order once using the fetched bill.
    The account is derived from the bill server-side — no accountReferenceId needed.
    Returns the full `data` dict (orderReferenceId, pgTransactionId, amount …).
    """
    bill_amount = fetched_bill["amount"]
    resp = client.post(
        "/gw/v1/bbps/order",
        payload={
            "items": [
                {
                    "billReferenceId": fetched_bill["billReferenceId"],
                    "amountType": "TOTAL_DUE",
                    "amount": bill_amount,
                }
            ],
            "paymentModes": [
                {
                    "provider": "UPI",
                    "amount": bill_amount,
                    "details": {
                        "paymentMode": "SAVINGS_ACCOUNT",
                        "payer": {
                            "fromAccount": settings.TEST_VPA,
                            "fromVpa": settings.TEST_VPA,
                            "mobileNumber": settings.TEST_PHONE,
                        },
                    },
                }
            ],
        },
    )
    assert resp.ok, f"create-order failed: {resp}"
    assert resp.data.get("orderReferenceId"), "No orderReferenceId in response"
    return resp.data

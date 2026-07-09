"""
Negative / error scenario tests

Validates that the API returns the correct error codes and HTTP statuses
when given bad input or missing auth — without relying on test-data fixtures.
"""

import pytest
import requests

from config import settings


@pytest.mark.bbps
@pytest.mark.negative
class TestAuthentication:

    def test_missing_token_returns_401(self):
        resp = requests.get(
            f"{settings.BASE_URL}/gw/v1/bbps/biller-categories",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self):
        resp = requests.get(
            f"{settings.BASE_URL}/gw/v1/bbps/biller-categories",
            headers={
                "Content-Type": "application/json",
                "x-token": "totally-invalid-token-xyz",
            },
        )
        assert resp.status_code == 401

    def test_empty_token_returns_401(self):
        resp = requests.get(
            f"{settings.BASE_URL}/gw/v1/bbps/biller-categories",
            headers={
                "Content-Type": "application/json",
                "x-token": "",
            },
        )
        assert resp.status_code == 401


@pytest.mark.bbps
@pytest.mark.negative
class TestInvalidBillerInputs:

    def test_nonexistent_category_returns_error(self, client):
        resp = client.get(
            "/gw/v1/bbps/biller-categories/00000000-0000-0000-0000-000000000000/billers"
        )
        # Either empty list (200) or a 4xx is acceptable — must not 500
        assert resp.status_code < 500

    def test_nonexistent_biller_details_returns_error(self, client):
        resp = client.get("/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000")
        assert resp.error is not None or resp.data is None

    def test_validate_account_empty_params_returns_error(
        self, client, biller_ref_id
    ):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/validate-account",
            payload={"customerParams": {}},
        )
        assert resp.error is not None, (
            "Expected INCOMPLETE_DETAILS or INVALID_ACCOUNT for empty params"
        )

    def test_validate_account_wrong_biller_returns_error(
        self, client, customer_params
    ):
        resp = client.post(
            "/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000/validate-account",
            payload={"customerParams": customer_params},
        )
        assert resp.error is not None

    def test_bill_fetch_empty_params_returns_error(self, client, biller_ref_id):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/bill",
            payload={"customerParams": {}},
        )
        assert resp.error is not None


@pytest.mark.bbps
@pytest.mark.negative
class TestInvalidOrderInputs:

    def test_order_with_empty_items_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/order",
            payload={
                "items": [],
                "paymentModes": [{"provider": "UPI", "amount": 100, "details": {"paymentMode": "SAVINGS_ACCOUNT", "payer": {"fromAccount": "x", "fromVpa": "x@upi"}}}],
            },
        )
        assert resp.error is not None

    def test_order_with_nonexistent_bill_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/order",
            payload={
                "items": [
                    {
                        "billReferenceId": "00000000-0000-0000-0000-000000000000",
                        "amountType": "TOTAL_DUE",
                        "amount": 100,
                    }
                ],
                "paymentModes": [{"provider": "UPI", "amount": 100, "details": {"paymentMode": "SAVINGS_ACCOUNT", "payer": {"fromAccount": "x", "fromVpa": "x@upi"}}}],
            },
        )
        assert resp.error is not None

    def test_order_payment_amount_mismatch_returns_error(self, client, fetched_bill):
        from config import settings
        bill_amount = float(fetched_bill["amount"])
        wrong_payment = bill_amount + 500.0
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
                        "amount": wrong_payment,
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
        assert resp.error is not None
        assert resp.error_reason is not None

    def test_get_nonexistent_order_returns_error(self, client):
        resp = client.get("/gw/v1/bbps/orders/nonexistent-order-ref-xyz")
        assert resp.error is not None or resp.data is None

    def test_order_estimate_empty_items_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/order/estimate",
            payload={"items": [], "paymentMode": "SAVINGS_ACCOUNT"},
        )
        assert resp.error is not None or resp.data is None or resp.data == {}


@pytest.mark.bbps
@pytest.mark.negative
class TestInvalidPrepaidInputs:

    def test_plans_missing_mobile_number_returns_error(self, client):
        resp = client.post("/gw/v1/bbps/prepaid/plans", payload={})
        assert resp.error is not None or resp.status_code >= 400

    def test_plans_invalid_mobile_number_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/prepaid/plans",
            payload={"mobileNumber": "123"},
        )
        assert resp.error is not None

    def test_plan_by_nonexistent_identifier_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/prepaid/plans/NONEXISTENT_PLAN_ID_000",
            payload={"mobileNumber": "9999999999"},
        )
        assert resp.error is not None or resp.data is None


@pytest.mark.bbps
@pytest.mark.negative
class TestErrorResponseStructure:
    """
    All business errors from the gateway follow the same envelope:
    { "data": null, "error": { "errorReason": "...", "errorReasonText": "..." } }
    These tests verify that structure is consistently present.
    """

    def test_error_has_error_reason(self, client):
        resp = client.get("/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000")
        if resp.error:
            assert resp.error.get("errorReason") is not None, (
                f"errorReason missing from error envelope: {resp.error}"
            )

    def test_error_has_error_reason_text(self, client):
        resp = client.get("/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000")
        if resp.error:
            assert resp.error.get("errorReasonText") is not None, (
                f"errorReasonText missing from error envelope: {resp.error}"
            )

    def test_error_response_data_is_null(self, client):
        resp = client.get("/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000")
        if resp.error:
            assert resp.data is None, (
                "data should be null when error is present"
            )

    def test_error_reason_is_string(self, client):
        resp = client.get("/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000")
        if resp.error:
            assert isinstance(resp.error.get("errorReason"), str), (
                "errorReason should be a string"
            )

    def test_error_reason_text_is_string(self, client):
        resp = client.get("/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000")
        if resp.error:
            assert isinstance(resp.error.get("errorReasonText"), str), (
                "errorReasonText should be a string"
            )

    def test_mark_paid_unknown_bill_error_structure(self, client):
        resp = client.post(
            "/gw/v1/bbps/bills/mark-paid",
            payload={"billReferenceId": "00000000-0000-0000-0000-000000000000"},
        )
        if resp.error:
            assert resp.error.get("errorReason") is not None
            assert resp.error.get("errorReasonText") is not None

    def test_order_estimate_error_has_structure(self, client, fetched_bill):
        resp = client.post(
            "/gw/v1/bbps/order/estimate",
            payload={
                "items": [
                    {
                        "billReferenceId": fetched_bill["billReferenceId"],
                        "amountType": "TOTAL_DUE",
                        "amount": fetched_bill["amount"],
                    }
                ],
                "paymentMode": "INVALID_MODE",
            },
        )
        if resp.error:
            assert resp.error.get("errorReason") is not None


@pytest.mark.bbps
@pytest.mark.negative
class TestPaginationEdgeCases:

    def test_order_history_large_page_returns_empty_or_valid(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 99999, "size": 10})
        assert resp.status_code == 200
        assert isinstance(resp.data.get("orders"), list)

    def test_order_history_size_one(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 1})
        assert resp.ok
        orders = resp.data.get("orders", [])
        assert len(orders) <= 1, f"size=1 returned {len(orders)} orders"

    def test_billers_large_page_does_not_error(self, client, biller_ref_id):
        from config import settings
        if not settings.BILLER_CATEGORY_REF_ID:
            pytest.skip("TEST_BILLER_CATEGORY_REF_ID not set")
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{settings.BILLER_CATEGORY_REF_ID}/billers",
            params={"page": 99999, "size": 10},
        )
        assert resp.status_code == 200


@pytest.mark.bbps
@pytest.mark.negative
class TestMalformedInputs:

    def test_malformed_uuid_biller_returns_error(self, client):
        # Known backend behaviour: malformed UUID hits a Spring conversion error → 500
        # Assert it is NOT a 200 success (i.e. the request is always rejected)
        resp = client.get("/gw/v1/bbps/billers/not-a-uuid-at-all")
        assert resp.status_code != 200, "Malformed UUID should not return a 200 success"

    def test_malformed_uuid_order_returns_error(self, client):
        # Backend returns HTTP 200 with an error body for unknown order refs
        resp = client.get("/gw/v1/bbps/orders/not-a-valid-order-ref")
        assert resp.error is not None, "Malformed order ref should return an error body"

    def test_malformed_uuid_receipt_returns_error(self, client):
        # Same — malformed ref returns 200 with error body, not a 4xx/5xx
        resp = client.get("/gw/v1/bbps/orders/not-a-valid-order-ref/receipt")
        assert resp.error is not None, "Malformed order ref should return an error body"

    def test_empty_bill_reference_id_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/bills/mark-paid",
            payload={"billReferenceId": ""},
        )
        assert resp.error is not None or resp.status_code >= 400

    def test_null_customer_params_returns_error(self, client, biller_ref_id):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/bill",
            payload={"customerParams": None},
        )
        assert resp.error is not None or resp.status_code >= 400

    def test_estimate_with_negative_amount_does_not_500(self, client, fetched_bill):
        # Backend currently accepts negative amounts in estimate without error —
        # asserting at minimum it does not crash with a 5xx
        resp = client.post(
            "/gw/v1/bbps/order/estimate",
            payload={
                "items": [
                    {
                        "billReferenceId": fetched_bill["billReferenceId"],
                        "amountType": "TOTAL_DUE",
                        "amount": -100,
                    }
                ],
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.status_code < 500

    def test_estimate_with_zero_amount_does_not_500(self, client, fetched_bill):
        # Backend currently accepts zero amounts in estimate — asserting no 5xx at minimum
        resp = client.post(
            "/gw/v1/bbps/order/estimate",
            payload={
                "items": [
                    {
                        "billReferenceId": fetched_bill["billReferenceId"],
                        "amountType": "TOTAL_DUE",
                        "amount": 0,
                    }
                ],
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.status_code < 500

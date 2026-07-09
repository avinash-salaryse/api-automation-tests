"""
Bill fetch flow tests
  POST /gw/v1/bbps/billers/{id}/validate-account
  POST /gw/v1/bbps/billers/{id}/bill
"""

import pytest


@pytest.mark.bbps
@pytest.mark.bill_fetch
@pytest.mark.smoke
class TestValidateAccount:

    def test_returns_200(self, client, biller_ref_id, customer_params):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/validate-account",
            payload={"customerParams": customer_params},
        )
        assert resp.status_code == 200

    def test_no_error_in_response(self, client, biller_ref_id, customer_params):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/validate-account",
            payload={"customerParams": customer_params},
        )
        # Some sandbox billers return VALIDATION_NOT_SUPPORTED_PREPAID — treat as skip
        if resp.error_reason == "VALIDATION_NOT_SUPPORTED_PREPAID":
            pytest.skip("Biller does not support account validation in this environment")
        assert resp.error is None, f"Unexpected error: {resp.error}"

    def test_account_reference_id_returned(self, validated_account):
        assert validated_account.get("accountReferenceId"), (
            "accountReferenceId missing from validate-account response"
        )

    def test_account_reference_id_is_uuid_format(self, validated_account):
        ref_id = validated_account["accountReferenceId"]
        parts = ref_id.split("-")
        assert len(parts) == 5, f"accountReferenceId is not UUID format: {ref_id}"

    def test_amount_limits_present(self, validated_account):
        assert validated_account.get("maxAmountAllowed") is not None, (
            "maxAmountAllowed missing"
        )
        assert validated_account.get("minAmountAllowed") is not None, (
            "minAmountAllowed missing"
        )

    def test_min_amount_not_greater_than_max(self, validated_account):
        min_amt = float(validated_account["minAmountAllowed"])
        max_amt = float(validated_account["maxAmountAllowed"])
        assert min_amt <= max_amt, (
            f"minAmountAllowed ({min_amt}) > maxAmountAllowed ({max_amt})"
        )

    def test_idempotent_same_params_return_same_account(
        self, client, biller_ref_id, customer_params, validated_account
    ):
        # Second call with same params should return the same accountReferenceId
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/validate-account",
            payload={"customerParams": customer_params},
        )
        assert resp.ok
        assert resp.data["accountReferenceId"] == validated_account["accountReferenceId"]

    def test_missing_required_params_returns_error(self, client, biller_ref_id):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/validate-account",
            payload={"customerParams": {}},
        )
        assert resp.error is not None, "Expected error for empty customerParams"

    def test_invalid_biller_id_returns_error(self, client, customer_params):
        resp = client.post(
            "/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000/validate-account",
            payload={"customerParams": customer_params},
        )
        assert resp.error is not None, "Expected error for non-existent biller"


@pytest.mark.bbps
@pytest.mark.bill_fetch
@pytest.mark.smoke
class TestFetchBill:

    def test_returns_200(self, client, biller_ref_id, customer_params):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/bill",
            payload={"customerParams": customer_params},
        )
        assert resp.status_code == 200

    def test_no_error_in_response(self, client, biller_ref_id, customer_params):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/bill",
            payload={"customerParams": customer_params},
        )
        _TRANSIENT = {"BILL_NOT_AVAILABLE", "BBPSERR001", "ALL-SITE-DOWN-FOR-ROUTE", "BILLER_NOT_AVAILABLE"}
        if resp.error_reason in _TRANSIENT:
            pytest.skip(f"Biller returned transient error {resp.error_reason}")
        assert resp.error is None, f"Unexpected error: {resp.error}"

    def test_bill_reference_id_returned(self, fetched_bill):
        assert fetched_bill.get("billReferenceId"), (
            "billReferenceId missing from bill fetch response"
        )

    def test_bill_amount_is_positive(self, fetched_bill):
        amount = fetched_bill.get("amount")
        assert amount is not None, "amount missing from bill"
        assert float(amount) > 0, f"Bill amount should be positive, got: {amount}"

    def test_due_date_present(self, fetched_bill):
        assert fetched_bill.get("dueDate") is not None, "dueDate missing from bill"

    def test_amount_within_biller_limits(self, fetched_bill, validated_account):
        amount = float(fetched_bill["amount"])
        min_amt = float(validated_account["minAmountAllowed"])
        max_amt = float(validated_account["maxAmountAllowed"])
        assert min_amt <= amount <= max_amt, (
            f"Bill amount {amount} outside biller limits [{min_amt}, {max_amt}]"
        )

    def test_repeated_fetch_returns_valid_bill_reference(
        self, client, biller_ref_id, customer_params
    ):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/bill",
            payload={"customerParams": customer_params},
        )
        _TRANSIENT = {"BILL_NOT_AVAILABLE", "BBPSERR001", "ALL-SITE-DOWN-FOR-ROUTE", "BILLER_NOT_AVAILABLE"}
        if resp.error_reason in _TRANSIENT:
            pytest.skip(f"Biller returned transient error {resp.error_reason}")
        assert resp.ok
        # Each fetch may create a new bill entity; just verify a valid reference is returned
        assert resp.data.get("billReferenceId"), "billReferenceId missing from bill fetch"

    def test_missing_customer_params_returns_error(self, client, biller_ref_id):
        resp = client.post(
            f"/gw/v1/bbps/billers/{biller_ref_id}/bill",
            payload={"customerParams": {}},
        )
        assert resp.error is not None, "Expected error for empty customerParams"


@pytest.mark.bbps
@pytest.mark.bill_fetch
class TestBillFetchFields:
    """Validates all key fields in the bill fetch response."""

    def test_bill_date_present(self, fetched_bill):
        assert fetched_bill.get("billDate") is not None, "billDate missing from bill"

    def test_bill_reference_id_is_uuid_format(self, fetched_bill):
        ref_id = fetched_bill.get("billReferenceId", "")
        assert len(ref_id.split("-")) == 5, (
            f"billReferenceId is not UUID format: {ref_id}"
        )

    def test_amount_is_numeric(self, fetched_bill):
        float(fetched_bill["amount"])  # must not raise

    def test_allows_upi_credit_card_present(self, fetched_bill):
        assert "allowsUpiCreditCard" in fetched_bill, (
            "allowsUpiCreditCard missing from bill response"
        )

    def test_allows_upi_credit_card_is_boolean(self, fetched_bill):
        val = fetched_bill.get("allowsUpiCreditCard")
        if val is not None:
            assert isinstance(val, bool), "allowsUpiCreditCard should be boolean"

    def test_min_amount_due_is_numeric_when_present(self, fetched_bill):
        # minAmountDue is optional — not all billers return it
        if "minAmountDue" in fetched_bill and fetched_bill["minAmountDue"] is not None:
            float(fetched_bill["minAmountDue"])  # must be numeric

    def test_processing_fee_key_present(self, fetched_bill):
        assert "processingFee" in fetched_bill, "processingFee key missing from bill"

    def test_due_date_is_string(self, fetched_bill):
        assert isinstance(fetched_bill.get("dueDate"), str), (
            "dueDate should be a string"
        )

    def test_account_holder_name_key_present(self, fetched_bill):
        assert "accountHolderName" in fetched_bill, (
            "accountHolderName key missing from bill"
        )


@pytest.mark.bbps
@pytest.mark.bill_fetch
class TestValidateAccountFields:
    """Validates all key fields in the validate-account response."""

    def test_allows_upi_credit_card_present(self, validated_account):
        assert "allowsUpiCreditCard" in validated_account, (
            "allowsUpiCreditCard missing from validate-account response"
        )

    def test_max_amount_is_numeric(self, validated_account):
        float(validated_account["maxAmountAllowed"])  # must not raise

    def test_min_amount_is_numeric(self, validated_account):
        float(validated_account["minAmountAllowed"])  # must not raise

    def test_account_reference_id_is_non_empty(self, validated_account):
        assert len(validated_account["accountReferenceId"]) > 0

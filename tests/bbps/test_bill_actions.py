"""
Bill action + dashboard tests
  POST /gw/v1/bbps/bills/mark-paid
  POST /gw/v1/bbps/bills/deactivate-account
  GET  /gw/v1/bbps/dashboard
  GET  /gw/v1/bbps/cub/biller-details
"""

import pytest

from config import settings


@pytest.fixture(scope="class")
def bill_for_mark_paid(client):
    """Fetches a fresh bill dedicated to mark-paid tests.

    Uses a separate fetch so the session-scoped ``fetched_bill`` used by order
    tests is never marked as paid before those tests run.
    """
    if not settings.BILLER_REF_ID or not settings.CUSTOMER_PARAMS:
        pytest.skip("TEST_BILLER_REF_ID / TEST_CUSTOMER_PARAMS not set")
    resp = client.post(
        f"/gw/v1/bbps/billers/{settings.BILLER_REF_ID}/bill",
        payload={"customerParams": settings.CUSTOMER_PARAMS},
    )
    if not resp.ok:
        pytest.skip(f"Could not fetch a bill for mark-paid tests: {resp}")
    return resp.data


@pytest.mark.bbps
@pytest.mark.bill_actions
class TestMarkBillAsPaid:
    """
    Marks a bill as user-paid (MARKED_PAID_BY_USER).
    This does NOT trigger the payment flow — it is a user-side annotation.
    Uses its own bill fixture so the shared fetched_bill stays PENDING for order tests.
    """

    def test_returns_200(self, client, bill_for_mark_paid):
        resp = client.post(
            "/gw/v1/bbps/bills/mark-paid",
            payload={"billReferenceId": bill_for_mark_paid["billReferenceId"]},
        )
        assert resp.status_code == 200

    def test_no_error_on_mark_paid(self, client, bill_for_mark_paid):
        resp = client.post(
            "/gw/v1/bbps/bills/mark-paid",
            payload={"billReferenceId": bill_for_mark_paid["billReferenceId"]},
        )
        assert resp.error is None, f"Unexpected error: {resp.error}"

    def test_missing_bill_reference_returns_error(self, client):
        resp = client.post("/gw/v1/bbps/bills/mark-paid", payload={})
        assert resp.error is not None or resp.status_code >= 400

    def test_nonexistent_bill_reference_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/bills/mark-paid",
            payload={"billReferenceId": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.error is not None, "Expected error for non-existent bill"


@pytest.mark.bbps
@pytest.mark.bill_actions
@pytest.mark.destructive
class TestDeactivateAccount:
    """
    Deactivates an account (sets active=false).
    Marked `destructive` — do not run alongside tests that depend on the
    validated_account fixture, or run this last with:
      pytest -m destructive
    """

    def test_returns_200(self, client, validated_account):
        resp = client.post(
            "/gw/v1/bbps/bills/deactivate-account",
            payload={"accountReferenceId": validated_account["accountReferenceId"]},
        )
        assert resp.status_code == 200

    def test_no_error_on_deactivate(self, client, validated_account):
        resp = client.post(
            "/gw/v1/bbps/bills/deactivate-account",
            payload={"accountReferenceId": validated_account["accountReferenceId"]},
        )
        assert resp.error is None, f"Unexpected error: {resp.error}"

    def test_missing_account_reference_returns_error(self, client):
        resp = client.post("/gw/v1/bbps/bills/deactivate-account", payload={})
        assert resp.error is not None or resp.status_code >= 400

    def test_nonexistent_account_reference_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/bills/deactivate-account",
            payload={"accountReferenceId": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.error is not None, "Expected error for non-existent account"


@pytest.mark.bbps
@pytest.mark.bill_actions
@pytest.mark.smoke
class TestDashboard:

    def test_returns_200(self, client):
        resp = client.get("/gw/v1/bbps/dashboard")
        assert resp.status_code == 200

    def test_no_error_in_response(self, client):
        resp = client.get("/gw/v1/bbps/dashboard")
        assert resp.error is None

    def test_dashboard_data_present(self, client):
        resp = client.get("/gw/v1/bbps/dashboard")
        assert resp.data is not None, "Dashboard data is null"


@pytest.mark.bbps
@pytest.mark.bill_actions
class TestCubBillerDetails:

    def test_returns_200(self, client):
        resp = client.get("/gw/v1/bbps/cub/biller-details")
        assert resp.status_code == 200

    def test_response_is_valid(self, client):
        resp = client.get("/gw/v1/bbps/cub/biller-details")
        # CUB biller may not be available for all users — either data or error is valid
        assert resp.status_code == 200

    def test_data_or_error_present(self, client):
        resp = client.get("/gw/v1/bbps/cub/biller-details")
        assert resp.data is not None or resp.error is not None, (
            "Response has neither data nor error"
        )

    def test_no_server_error(self, client):
        resp = client.get("/gw/v1/bbps/cub/biller-details")
        # Must not be a 5xx even if the user doesn't have a CUB account
        assert resp.status_code < 500


@pytest.mark.bbps
@pytest.mark.bill_actions
class TestDashboardStructure:
    """Validates the dashboard response structure in detail."""

    def test_dashboard_data_is_dict(self, client):
        resp = client.get("/gw/v1/bbps/dashboard")
        assert resp.ok
        if resp.data is not None:
            assert isinstance(resp.data, dict), "Dashboard data should be a dict"

    def test_dashboard_response_consistent_across_calls(self, client):
        resp1 = client.get("/gw/v1/bbps/dashboard")
        resp2 = client.get("/gw/v1/bbps/dashboard")
        assert resp1.status_code == resp2.status_code == 200
        # Both calls should succeed without errors
        assert resp1.error is None and resp2.error is None


@pytest.mark.bbps
@pytest.mark.bill_actions
class TestMarkPaidIdempotency:
    """Marking a bill as paid a second time should not cause a server error."""

    @pytest.fixture(scope="class")
    def bill_for_idempotency(self, client):
        if not settings.BILLER_REF_ID or not settings.CUSTOMER_PARAMS:
            pytest.skip("TEST_BILLER_REF_ID / TEST_CUSTOMER_PARAMS not set")
        resp = client.post(
            f"/gw/v1/bbps/billers/{settings.BILLER_REF_ID}/bill",
            payload={"customerParams": settings.CUSTOMER_PARAMS},
        )
        if not resp.ok:
            pytest.skip(f"Could not fetch a bill: {resp}")
        return resp.data

    def test_first_mark_paid_succeeds(self, client, bill_for_idempotency):
        resp = client.post(
            "/gw/v1/bbps/bills/mark-paid",
            payload={"billReferenceId": bill_for_idempotency["billReferenceId"]},
        )
        assert resp.status_code == 200

    def test_second_mark_paid_does_not_500(self, client, bill_for_idempotency):
        # Second call on same bill — may return error or succeed, but must not 500
        resp = client.post(
            "/gw/v1/bbps/bills/mark-paid",
            payload={"billReferenceId": bill_for_idempotency["billReferenceId"]},
        )
        assert resp.status_code < 500

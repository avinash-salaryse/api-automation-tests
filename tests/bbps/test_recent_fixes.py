"""
Tests for recent BBPS backend fixes and features.

Covers:
  - quickPaymentData non-null on biller search (fix a670c3d)
  - scoinApplicablePoints in create-order response (feats bf4da45 / 760530d)
  - scoinApplicableAmount + scoinApplicablePoints in order details + history
    (feats ac26cf9 / 760530d)

Notes on field presence vs. null:
  Spring Boot omits JSON keys whose value is null by default.
  Tests below use .get() so they pass whether the key is absent (null omitted)
  or explicitly null — the important contract is that the value is not present
  / not set for non-scoin orders.
"""

import pytest


@pytest.mark.bbps
@pytest.mark.discovery
class TestQuickPaymentDataOnSearch:
    """
    Regression: biller search with a non-blank query was returning null
    quickPaymentData. After the fix (a670c3d) it must always be a non-null
    dict with a quickPaymentOptions list — never null.

    Actual shape: {"headerText": "...", "quickPaymentOptions": [...]}
    """

    def test_search_quick_payment_data_key_present(
        self, client, biller_category_ref_id
    ):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "Air"},
        )
        assert resp.ok
        assert "quickPaymentData" in resp.data, (
            "quickPaymentData key missing from biller-by-category response"
        )

    def test_search_quick_payment_data_is_not_null(
        self, client, biller_category_ref_id
    ):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "Air"},
        )
        assert resp.ok
        assert resp.data["quickPaymentData"] is not None, (
            "quickPaymentData must not be null when a search term is provided"
        )

    def test_search_quick_payment_data_is_dict(
        self, client, biller_category_ref_id
    ):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "Air"},
        )
        assert resp.ok
        quick = resp.data["quickPaymentData"]
        assert isinstance(quick, dict), (
            f"quickPaymentData should be a dict, got {type(quick)}"
        )

    def test_search_quick_payment_options_is_empty_list(
        self, client, biller_category_ref_id
    ):
        # quickPaymentOptions (recent payments) are always hidden during search
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "Air"},
        )
        assert resp.ok
        options = resp.data["quickPaymentData"]["quickPaymentOptions"]
        assert isinstance(options, list), "quickPaymentOptions should be a list"
        assert len(options) == 0, (
            "quickPaymentOptions should be empty during biller search"
        )

    def test_no_results_search_quick_payment_data_is_not_null(
        self, client, biller_category_ref_id
    ):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "xyznonexistent999abc"},
        )
        assert resp.ok
        assert resp.data.get("quickPaymentData") is not None, (
            "quickPaymentData must not be null even when search returns no biller results"
        )
        assert isinstance(resp.data["quickPaymentData"], dict)

    def test_no_search_quick_payment_data_has_options_list(
        self, client, biller_category_ref_id
    ):
        # Without a search term, quickPaymentData is a dict with quickPaymentOptions list
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers"
        )
        assert resp.ok
        quick = resp.data.get("quickPaymentData")
        if quick is not None:
            assert isinstance(quick, dict), (
                f"quickPaymentData should be a dict, got {type(quick)}"
            )
            assert "quickPaymentOptions" in quick, (
                "quickPaymentData missing quickPaymentOptions key"
            )
            assert isinstance(quick["quickPaymentOptions"], list)


@pytest.mark.bbps
@pytest.mark.order
class TestCreateOrderScoinFields:
    """
    Verifies fields in the create-order response related to scoin and
    net PG-payable amount.

      - scoinApplicablePoints: absent or null for pure-UPI orders
      - amount: net PG-payable (equals bill amount when no scoin is applied)

    (feats bf4da45, 760530d)
    """

    def test_scoin_applicable_points_absent_or_null_for_pure_upi(self, created_order):
        # Spring omits null fields — absent and null are both correct for non-scoin orders
        assert created_order.get("scoinApplicablePoints") is None, (
            "scoinApplicablePoints should be absent or null for a pure UPI (non-scoin) order"
        )

    def test_amount_equals_bill_amount_for_pure_upi(
        self, created_order, fetched_bill
    ):
        # No scoin applied → pgPayable == bill amount
        assert float(created_order["amount"]) == float(fetched_bill["amount"]), (
            "create-order amount should equal bill amount for a pure UPI order "
            "(no scoin deduction applied)"
        )

    def test_amount_is_non_negative(self, created_order):
        assert float(created_order["amount"]) >= 0, (
            f"create-order amount must be non-negative, got {created_order['amount']}"
        )

    def test_amount_is_numeric(self, created_order):
        float(created_order["amount"])  # must not raise


@pytest.mark.bbps
@pytest.mark.order
class TestOrderDetailsScoinFields:
    """
    Verifies scoin fields in GET /gw/v1/bbps/orders/{id}.

      - scoinApplicableAmount: absent or null for pure-UPI orders
      - scoinApplicablePoints: absent or null for pure-UPI orders
      - totalAmount: gross order amount regardless of any scoin split

    (feats ac26cf9, 760530d)
    """

    def test_scoin_applicable_amount_absent_or_null_for_pure_upi(
        self, client, created_order
    ):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok
        assert resp.data.get("scoinApplicableAmount") is None, (
            "scoinApplicableAmount should be absent or null for a pure UPI order"
        )

    def test_scoin_applicable_points_absent_or_null_for_pure_upi(
        self, client, created_order
    ):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok
        assert resp.data.get("scoinApplicablePoints") is None, (
            "scoinApplicablePoints should be absent or null for a pure UPI order"
        )

    def test_total_amount_equals_bill_amount(self, client, created_order, fetched_bill):
        # totalAmount is the gross order amount — unaffected by scoin deductions
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok
        assert float(resp.data["totalAmount"]) == float(fetched_bill["amount"]), (
            "totalAmount in order details should equal the original bill amount "
            "(gross, before any scoin deduction)"
        )

    def test_total_amount_is_numeric(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok
        float(resp.data["totalAmount"])  # must not raise

    def test_order_details_not_broken_by_scoin_changes(self, client, created_order):
        # Smoke: order details still return cleanly after scoin field changes
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok, f"Order details returned error: {resp.error}"
        assert resp.data.get("orderReferenceId") == created_order["orderReferenceId"]


@pytest.mark.bbps
@pytest.mark.order
class TestOrderHistoryScoinFields:
    """
    Verifies scoin fields in order history items from GET /gw/v1/bbps/orders.
    For pure-UPI orders both fields are absent or null.
    """

    def test_created_order_scoin_amount_absent_or_null_in_history(
        self, client, created_order
    ):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 20})
        assert resp.ok
        target = next(
            (
                o for o in resp.data.get("orders", [])
                if o.get("orderReferenceId") == created_order["orderReferenceId"]
            ),
            None,
        )
        assert target is not None, (
            "Created order not found in order history — increase page size or check env"
        )
        assert target.get("scoinApplicableAmount") is None, (
            "scoinApplicableAmount should be absent or null for a non-scoin order in history"
        )

    def test_created_order_scoin_points_absent_or_null_in_history(
        self, client, created_order
    ):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 20})
        assert resp.ok
        target = next(
            (
                o for o in resp.data.get("orders", [])
                if o.get("orderReferenceId") == created_order["orderReferenceId"]
            ),
            None,
        )
        assert target is not None, (
            "Created order not found in order history — increase page size or check env"
        )
        assert target.get("scoinApplicablePoints") is None, (
            "scoinApplicablePoints should be absent or null for a non-scoin order in history"
        )

    def test_all_history_items_scoin_amount_absent_or_null(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.ok
        for order in resp.data.get("orders", []):
            val = order.get("scoinApplicableAmount")
            # If present, must be a number (scoin was applied); if absent/null, fine for pure-UPI
            if val is not None:
                float(val)  # must be numeric when present

    def test_all_history_items_scoin_points_absent_or_null(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.ok
        for order in resp.data.get("orders", []):
            val = order.get("scoinApplicablePoints")
            # If present, must be an integer; if absent/null, fine for pure-UPI
            if val is not None:
                assert isinstance(val, int), (
                    f"scoinApplicablePoints should be an integer when present, got {type(val)}"
                )

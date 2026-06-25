"""
Tests for recent BBPS backend fixes and features.

Covers:
  - quickPaymentData non-null on biller search (fix a670c3d)
  - scoinApplicablePoints in create-order response (feats bf4da45 / 760530d)
  - scoinApplicableAmount + scoinApplicablePoints in order details + history
    (feats ac26cf9 / 760530d)
"""

import pytest


@pytest.mark.bbps
@pytest.mark.discovery
class TestQuickPaymentDataOnSearch:
    """
    Regression: biller search with a non-blank query was returning null
    quickPaymentData. After the fix (a670c3d) it must always be a list
    (possibly empty) — never null.
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

    def test_search_quick_payment_data_is_list(
        self, client, biller_category_ref_id
    ):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "Air"},
        )
        assert resp.ok
        assert isinstance(resp.data["quickPaymentData"], list), (
            "quickPaymentData should be a list (possibly empty) for a search query"
        )

    def test_search_quick_payment_data_is_empty(
        self, client, biller_category_ref_id
    ):
        # Quick-pay entries (recent payments) are always hidden during search
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "Air"},
        )
        assert resp.ok
        assert len(resp.data["quickPaymentData"]) == 0, (
            "quickPaymentData should be an empty list during biller search"
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
        assert isinstance(resp.data["quickPaymentData"], list)

    def test_no_search_quick_payment_data_is_null_or_list(
        self, client, biller_category_ref_id
    ):
        # Without a search term, quickPaymentData is populated or null — both valid
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers"
        )
        assert resp.ok
        quick = resp.data.get("quickPaymentData")
        assert quick is None or isinstance(quick, list), (
            "Without a search term, quickPaymentData should be null or a list, "
            f"got {type(quick)}"
        )


@pytest.mark.bbps
@pytest.mark.order
class TestCreateOrderScoinFields:
    """
    Verifies new fields in the create-order response related to scoin and
    net PG-payable amount.

      - scoinApplicablePoints: points applicable to this order (null for pure-UPI)
      - amount: net PG-payable (equals bill amount when no scoin is applied)

    (feats bf4da45, 760530d)
    """

    def test_scoin_applicable_points_key_present(self, created_order):
        assert "scoinApplicablePoints" in created_order, (
            "scoinApplicablePoints key missing from create-order response"
        )

    def test_scoin_applicable_points_null_for_pure_upi(self, created_order):
        assert created_order.get("scoinApplicablePoints") is None, (
            "scoinApplicablePoints should be null for a pure UPI (non-scoin) order"
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


@pytest.mark.bbps
@pytest.mark.order
class TestOrderDetailsScoinFields:
    """
    Verifies scoin fields added to GET /gw/v1/bbps/orders/{id}.

      - scoinApplicableAmount: INR value of scoin applied (null for pure-UPI)
      - scoinApplicablePoints: points applied (null for pure-UPI)
      - totalAmount: gross order amount regardless of any scoin split

    (feats ac26cf9, 760530d)
    """

    def test_scoin_applicable_amount_key_present(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok
        assert "scoinApplicableAmount" in resp.data, (
            "scoinApplicableAmount key missing from order details response"
        )

    def test_scoin_applicable_points_key_present(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok
        assert "scoinApplicablePoints" in resp.data, (
            "scoinApplicablePoints key missing from order details response"
        )

    def test_scoin_applicable_amount_null_for_pure_upi(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok
        assert resp.data.get("scoinApplicableAmount") is None, (
            "scoinApplicableAmount should be null for a pure UPI (non-scoin) order"
        )

    def test_scoin_applicable_points_null_for_pure_upi(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}"
        )
        assert resp.ok
        assert resp.data.get("scoinApplicablePoints") is None, (
            "scoinApplicablePoints should be null for a pure UPI (non-scoin) order"
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


@pytest.mark.bbps
@pytest.mark.order
class TestOrderHistoryScoinFields:
    """
    Verifies scoin fields are present in each item returned by
    GET /gw/v1/bbps/orders (order history).
    """

    def test_created_order_in_history_has_scoin_applicable_amount(
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
        assert "scoinApplicableAmount" in target, (
            "scoinApplicableAmount key missing from order history item"
        )

    def test_created_order_in_history_has_scoin_applicable_points(
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
        assert "scoinApplicablePoints" in target, (
            "scoinApplicablePoints key missing from order history item"
        )

    def test_all_history_items_have_scoin_applicable_amount(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.ok
        for order in resp.data.get("orders", []):
            assert "scoinApplicableAmount" in order, (
                "scoinApplicableAmount missing from history order: "
                f"{order.get('orderReferenceId')}"
            )

    def test_all_history_items_have_scoin_applicable_points(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.ok
        for order in resp.data.get("orders", []):
            assert "scoinApplicablePoints" in order, (
                "scoinApplicablePoints missing from history order: "
                f"{order.get('orderReferenceId')}"
            )

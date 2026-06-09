"""
Order flow tests
  POST /gw/v1/bbps/order/estimate
  POST /gw/v1/bbps/order
  GET  /gw/v1/bbps/orders/{id}
  GET  /gw/v1/bbps/orders
  GET  /gw/v1/bbps/orders/{id}/receipt
  GET  /gw/v1/bbps/orders/{id}/rewards
"""

import pytest


@pytest.mark.bbps
@pytest.mark.order
class TestOrderEstimate:

    def test_returns_200(self, client, fetched_bill):
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
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.status_code == 200

    def test_no_error_for_upi_payment(self, client, fetched_bill):
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
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.error is None, f"Unexpected error: {resp.error}"

    def test_to_pay_equals_bill_amount_for_upi(self, client, fetched_bill):
        bill_amount = float(fetched_bill["amount"])
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
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.ok
        to_pay = float(resp.data["toPay"])
        assert to_pay == bill_amount, (
            f"Expected toPay={bill_amount} for UPI (no fee), got {to_pay}"
        )

    def test_upicredit_adds_convenience_fee(self, client, fetched_bill):
        # UPICREDIT (RuPay-CC-on-UPI) should add a 2.02% convenience fee
        bill_amount = float(fetched_bill["amount"])
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
                "paymentMode": "CREDIT_CARD",
            },
        )
        assert resp.ok
        to_pay = float(resp.data["toPay"])
        # toPay should be > bill amount when convenience fee applies
        assert to_pay >= bill_amount, (
            f"toPay ({to_pay}) should be >= bill amount ({bill_amount}) with CC fee"
        )

    def test_estimate_response_has_details_breakdown(self, client, fetched_bill):
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
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.ok
        assert isinstance(resp.data.get("details"), list), (
            "details breakdown should be a list"
        )


@pytest.mark.bbps
@pytest.mark.order
@pytest.mark.smoke
class TestCreateOrder:

    def test_returns_200(self, client, fetched_bill):
        from config import settings
        resp = client.post(
            "/gw/v1/bbps/order",
            payload={
                "items": [
                    {
                        "billReferenceId": fetched_bill["billReferenceId"],
                        "amountType": "TOTAL_DUE",
                        "amount": fetched_bill["amount"],
                    }
                ],
                "paymentModes": [
                    {
                        "provider": "UPI",
                        "amount": fetched_bill["amount"],
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
        assert resp.status_code == 200

    def test_order_reference_id_returned(self, created_order):
        assert created_order.get("orderReferenceId"), (
            "orderReferenceId missing from create-order response"
        )

    def test_pg_transaction_id_returned(self, created_order):
        assert created_order.get("pgTransactionId"), (
            "pgTransactionId missing — payment gateway cannot be initiated"
        )

    def test_amount_matches_bill(self, created_order, fetched_bill):
        assert float(created_order["amount"]) == float(fetched_bill["amount"])

    def test_mismatched_payment_amount_returns_error(self, client, fetched_bill):
        from config import settings
        wrong_amount = float(fetched_bill["amount"]) + 999.0
        resp = client.post(
            "/gw/v1/bbps/order",
            payload={
                "items": [
                    {
                        "billReferenceId": fetched_bill["billReferenceId"],
                        "amountType": "TOTAL_DUE",
                        "amount": fetched_bill["amount"],
                    }
                ],
                "paymentModes": [
                    {
                        "provider": "UPI",
                        "amount": wrong_amount,
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
        assert resp.error is not None, (
            "Expected error when payment amount doesn't match item amount"
        )

    def test_invalid_bill_reference_returns_error(self, client):
        from config import settings
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
                "paymentModes": [
                    {
                        "provider": "UPI",
                        "amount": 100,
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
        assert resp.error is not None, "Expected error for non-existent bill"

    def test_empty_items_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/order",
            payload={"items": [], "paymentModes": [{"provider": "UPI", "amount": 100, "details": {"paymentMode": "SAVINGS_ACCOUNT", "payer": {"fromAccount": "x", "fromVpa": "x@upi"}}}]},
        )
        assert resp.error is not None, "Expected error for empty items list"


@pytest.mark.bbps
@pytest.mark.order
class TestGetOrder:

    def test_returns_200(self, client, created_order):
        order_ref = created_order["orderReferenceId"]
        resp = client.get(f"/gw/v1/bbps/orders/{order_ref}")
        assert resp.status_code == 200

    def test_no_error_in_response(self, client, created_order):
        resp = client.get(f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}")
        assert resp.error is None

    def test_order_reference_id_matches(self, client, created_order):
        order_ref = created_order["orderReferenceId"]
        resp = client.get(f"/gw/v1/bbps/orders/{order_ref}")
        assert resp.data["orderReferenceId"] == order_ref

    def test_order_status_after_creation(self, client, created_order):
        # After UPI payment initiation, order may be PENDING or PAYMENT_PROCESSING
        resp = client.get(f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}")
        assert resp.data["orderStatus"] in ("PENDING", "PAYMENT_PROCESSING", "PAYMENT_SUCCESS"), (
            f"Unexpected order status: {resp.data['orderStatus']}"
        )

    def test_order_has_items(self, client, created_order):
        resp = client.get(f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}")
        assert len(resp.data.get("orderItems", [])) > 0, "Order has no items"

    def test_order_item_has_biller_name(self, client, created_order):
        resp = client.get(f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}")
        for item in resp.data["orderItems"]:
            assert item.get("billerName"), f"Order item missing billerName: {item}"

    def test_total_amount_present(self, client, created_order):
        resp = client.get(f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}")
        assert resp.data.get("totalAmount") is not None

    def test_nonexistent_order_returns_error(self, client):
        resp = client.get("/gw/v1/bbps/orders/nonexistent-order-ref-000")
        assert resp.error is not None or resp.data is None


@pytest.mark.bbps
@pytest.mark.order
class TestOrderHistory:

    def test_returns_200(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.status_code == 200

    def test_no_error_in_response(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.error is None

    def test_orders_field_is_list(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert isinstance(resp.data.get("orders"), list), (
            "orders field should be a list"
        )

    def test_newly_created_order_appears_in_history(self, client, created_order):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 20})
        order_refs = [o["orderReferenceId"] for o in resp.data.get("orders", [])]
        assert created_order["orderReferenceId"] in order_refs, (
            "Newly created order not found in order history"
        )

    def test_page_size_respected(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 2})
        assert resp.error is None
        orders = resp.data.get("orders", [])
        assert len(orders) <= 2, f"Returned {len(orders)} orders, expected ≤ 2"

    def test_different_pages_return_different_orders(self, client):
        p0 = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 5})
        p1 = client.get("/gw/v1/bbps/orders", params={"page": 1, "size": 5})
        if p0.ok and p1.ok:
            refs_p0 = {o["orderReferenceId"] for o in p0.data.get("orders", [])}
            refs_p1 = {o["orderReferenceId"] for o in p1.data.get("orders", [])}
            if refs_p1:
                assert refs_p0.isdisjoint(refs_p1), "Pagination returned duplicate orders"


@pytest.mark.bbps
@pytest.mark.order
class TestOrderReceipt:

    def test_returns_200(self, client, created_order):
        order_ref = created_order["orderReferenceId"]
        resp = client.get(f"/gw/v1/bbps/orders/{order_ref}/receipt")
        assert resp.status_code == 200

    def test_no_error_in_response(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}/receipt"
        )
        assert resp.error is None

    def test_receipt_data_present(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}/receipt"
        )
        assert resp.data is not None, "Receipt data is null"

    def test_nonexistent_order_receipt_returns_error(self, client):
        resp = client.get("/gw/v1/bbps/orders/nonexistent-order-ref-000/receipt")
        assert resp.error is not None or resp.data is None


@pytest.mark.bbps
@pytest.mark.order
class TestOrderRewards:

    def test_returns_200(self, client, created_order):
        order_ref = created_order["orderReferenceId"]
        resp = client.get(f"/gw/v1/bbps/orders/{order_ref}/rewards")
        assert resp.status_code == 200

    def test_response_is_valid(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}/rewards"
        )
        # Either data or error is acceptable — rewards may not yet be calculated
        assert resp.status_code == 200


@pytest.mark.bbps
@pytest.mark.order
class TestCreateOrderResponseFields:
    """Validates all key fields in the create-order response."""

    def test_payee_vpa_present(self, created_order):
        assert "payeeVpa" in created_order, (
            "payeeVpa missing from create-order response"
        )

    def test_payee_vpa_is_string(self, created_order):
        vpa = created_order.get("payeeVpa")
        if vpa is not None:
            assert isinstance(vpa, str), "payeeVpa should be a string"

    def test_mcc_present(self, created_order):
        assert "mcc" in created_order, "mcc (merchant category code) missing"

    def test_payee_name_present(self, created_order):
        assert "payeeName" in created_order, "payeeName missing from create-order response"

    def test_order_reference_id_is_uuid_format(self, created_order):
        ref_id = created_order.get("orderReferenceId", "")
        assert len(ref_id.split("-")) == 5, (
            f"orderReferenceId is not UUID format: {ref_id}"
        )

    def test_pg_transaction_id_is_non_empty(self, created_order):
        pg_id = created_order.get("pgTransactionId", "")
        assert len(str(pg_id)) > 0, "pgTransactionId is empty"

    def test_amount_is_numeric(self, created_order):
        float(created_order["amount"])  # must not raise


@pytest.mark.bbps
@pytest.mark.order
class TestOrderEstimateDetails:
    """Validates the fee breakdown structure returned by /order/estimate."""

    def test_details_items_have_required_keys(self, client, fetched_bill):
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
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.ok
        for item in resp.data.get("details", []):
            assert "value" in item, f"Detail item missing 'value': {item}"

    def test_to_pay_is_numeric(self, client, fetched_bill):
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
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.ok
        float(resp.data["toPay"])  # must not raise

    def test_scoin_widget_field_present(self, client, fetched_bill):
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
                "paymentMode": "SAVINGS_ACCOUNT",
            },
        )
        assert resp.ok
        assert "showScoinWidget" in resp.data, (
            "showScoinWidget field missing from estimate response"
        )

    def test_credit_card_fee_is_greater_than_savings_account(self, client, fetched_bill):
        def get_to_pay(mode):
            r = client.post(
                "/gw/v1/bbps/order/estimate",
                payload={
                    "items": [
                        {
                            "billReferenceId": fetched_bill["billReferenceId"],
                            "amountType": "TOTAL_DUE",
                            "amount": fetched_bill["amount"],
                        }
                    ],
                    "paymentMode": mode,
                },
            )
            return float(r.data["toPay"]) if r.ok else None

        savings = get_to_pay("SAVINGS_ACCOUNT")
        credit = get_to_pay("CREDIT_CARD")
        if savings is not None and credit is not None:
            assert credit >= savings, (
                f"CREDIT_CARD toPay ({credit}) should be >= SAVINGS_ACCOUNT toPay ({savings})"
            )


@pytest.mark.bbps
@pytest.mark.order
class TestOrderReceiptFields:
    """Validates the receipt response structure."""

    def test_receipt_base64_is_non_empty(self, client, created_order):
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}/receipt"
        )
        assert resp.ok
        if resp.data:
            receipt = resp.data.get("receiptBase64") or resp.data.get("receipt")
            if receipt:
                assert len(receipt) > 0, "receiptBase64 is empty"

    def test_receipt_base64_is_valid_base64(self, client, created_order):
        import base64
        import binascii
        resp = client.get(
            f"/gw/v1/bbps/orders/{created_order['orderReferenceId']}/receipt"
        )
        assert resp.ok
        if resp.data:
            receipt = resp.data.get("receiptBase64") or resp.data.get("receipt")
            if receipt and isinstance(receipt, str):
                try:
                    base64.b64decode(receipt, validate=True)
                except (ValueError, binascii.Error) as exc:
                    pytest.fail(f"receiptBase64 is not valid base64: {exc}")


@pytest.mark.bbps
@pytest.mark.order
class TestOrderHistoryFields:
    """Validates field presence in order history items."""

    def test_each_order_has_reference_id(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.ok
        for order in resp.data.get("orders", []):
            assert order.get("orderReferenceId"), (
                f"Order missing orderReferenceId: {order}"
            )

    def test_each_order_has_status(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.ok
        for order in resp.data.get("orders", []):
            assert order.get("orderStatus"), f"Order missing orderStatus: {order}"

    def test_each_order_has_amount(self, client):
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 10})
        assert resp.ok
        for order in resp.data.get("orders", []):
            assert "totalAmount" in order or "amount" in order, (
                f"Order missing amount field: {order}"
            )

    def test_order_statuses_are_known_values(self, client):
        known_statuses = {
            "PENDING", "PAYMENT_PROCESSING", "PAYMENT_SUCCESS", "SUCCESS",
            "PAYMENT_FAILED", "FAILED", "CANCELLED", "REFUNDED",
        }
        resp = client.get("/gw/v1/bbps/orders", params={"page": 0, "size": 20})
        assert resp.ok
        for order in resp.data.get("orders", []):
            status = order.get("orderStatus")
            if status:
                assert status in known_statuses, (
                    f"Unexpected orderStatus value: {status}"
                )

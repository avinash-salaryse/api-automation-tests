"""
Prepaid / recharge flow tests
  GET  /gw/v1/bbps/prepaid/operators
  GET  /gw/v1/bbps/prepaid/circles
  POST /gw/v1/bbps/prepaid/plans       (plans by mobile number)
  POST /gw/v1/bbps/prepaid/plans/{id}  (single plan details)
"""

import pytest


@pytest.mark.bbps
@pytest.mark.prepaid
@pytest.mark.smoke
class TestPrepaidOperators:

    def test_returns_200(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/operators")
        assert resp.status_code == 200

    def test_no_error_in_response(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/operators")
        assert resp.error is None

    def test_operators_list_not_empty(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/operators")
        operators = resp.data if isinstance(resp.data, list) else []
        assert len(operators) > 0, "Operators list is empty"

    def test_each_operator_has_code_and_name(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/operators")
        for op in resp.data or []:
            assert op.get("operatorCode"), f"Operator missing operatorCode: {op}"
            assert op.get("operatorName"), f"Operator missing operatorName: {op}"

    def test_known_operators_present(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/operators")
        names = [op["operatorName"].upper() for op in (resp.data or [])]
        known = {"AIRTEL", "JIO", "VI", "BSNL"}
        found = known & set(names)
        assert found, f"No known operators found. Got: {names}"


@pytest.mark.bbps
@pytest.mark.prepaid
@pytest.mark.smoke
class TestPrepaidCircles:

    def test_returns_200(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/circles")
        assert resp.status_code == 200

    def test_no_error_in_response(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/circles")
        assert resp.error is None

    def test_circles_list_not_empty(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/circles")
        circles = resp.data if isinstance(resp.data, list) else []
        assert len(circles) > 0, "Circles list is empty"

    def test_each_circle_has_ref_id_and_name(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/circles")
        for circle in resp.data or []:
            assert circle.get("circleRefId"), f"Circle missing circleRefId: {circle}"
            assert circle.get("circleName"), f"Circle missing circleName: {circle}"


@pytest.mark.bbps
@pytest.mark.prepaid
class TestPrepaidPlansByMobile:

    @pytest.fixture(scope="class")
    def plans_response(self, client, prepaid_mobile):
        """Fetches prepaid plans once; skips if operator cannot be detected."""
        resp = client.post(
            "/gw/v1/bbps/prepaid/plans",
            payload={"mobileNumber": prepaid_mobile},
        )
        if resp.error_reason == "operator_detection_failed":
            pytest.skip(
                f"Operator could not be detected for {prepaid_mobile} in this environment"
            )
        return resp

    def test_returns_200(self, plans_response):
        assert plans_response.status_code == 200

    def test_no_error_in_response(self, plans_response):
        assert plans_response.error is None, f"Unexpected error: {plans_response.error}"

    def test_mobile_number_echoed_back(self, plans_response, prepaid_mobile):
        assert plans_response.ok
        assert plans_response.data.get("mobileNumber") == prepaid_mobile

    def test_operator_detected(self, plans_response):
        resp = plans_response
        assert resp.ok
        assert resp.data.get("operatorCode"), "operatorCode not detected"
        assert resp.data.get("operatorName"), "operatorName not detected"

    def test_circle_detected(self, plans_response):
        resp = plans_response
        assert resp.ok
        assert resp.data.get("circleRefId"), "circleRefId not detected"
        assert resp.data.get("circleName"), "circleName not detected"

    def test_plans_list_not_empty(self, plans_response):
        resp = plans_response
        assert resp.ok
        plans = resp.data.get("plans", [])
        assert len(plans) > 0, "No plans returned for mobile number"

    def test_each_plan_has_denomination_and_validity(self, plans_response):
        resp = plans_response
        assert resp.ok
        for plan in resp.data.get("plans", []):
            assert plan.get("denomination") is not None, f"Plan missing denomination: {plan}"
            assert plan.get("validity") is not None, f"Plan missing validity: {plan}"

    def test_with_explicit_operator_and_circle(self, client, prepaid_mobile):
        if not (pytest.importorskip("config.settings").PREPAID_OPERATOR
                and pytest.importorskip("config.settings").PREPAID_CIRCLE_REF_ID):
            pytest.skip("TEST_PREPAID_OPERATOR and TEST_PREPAID_CIRCLE_REF_ID not set")
        from config import settings
        resp = client.post(
            "/gw/v1/bbps/prepaid/plans",
            payload={
                "mobileNumber": prepaid_mobile,
                "operatorCode": settings.PREPAID_OPERATOR,
                "circleRefId": settings.PREPAID_CIRCLE_REF_ID,
            },
        )
        assert resp.ok

    def test_missing_mobile_number_returns_error(self, client):
        resp = client.post("/gw/v1/bbps/prepaid/plans", payload={})
        assert resp.error is not None or resp.status_code >= 400, (
            "Expected error for missing mobileNumber"
        )

    def test_invalid_mobile_number_returns_error(self, client):
        resp = client.post(
            "/gw/v1/bbps/prepaid/plans",
            payload={"mobileNumber": "000"},
        )
        assert resp.error is not None, "Expected error for invalid mobile number"



@pytest.mark.bbps
@pytest.mark.prepaid
class TestPrepaidPlanByIdentifier:

    @pytest.fixture(scope="class")
    def plan_identifier(self, client, prepaid_mobile):
        """Grab the first plan identifier from the plans-by-mobile response."""
        resp = client.post(
            "/gw/v1/bbps/prepaid/plans",
            payload={"mobileNumber": prepaid_mobile},
        )
        plans = resp.data.get("plans", []) if resp.ok else []
        if not plans:
            pytest.skip("No plans available to test plan-by-identifier")
        identifier = plans[0].get("planIdentifier") or plans[0].get("payuPlanId")
        if not identifier:
            pytest.skip("Plan has no identifier field")
        return identifier

    def test_returns_200(self, client, prepaid_mobile, plan_identifier):
        resp = client.post(
            f"/gw/v1/bbps/prepaid/plans/{plan_identifier}",
            payload={"mobileNumber": prepaid_mobile},
        )
        assert resp.status_code == 200

    def test_no_error_in_response(self, client, prepaid_mobile, plan_identifier):
        resp = client.post(
            f"/gw/v1/bbps/prepaid/plans/{plan_identifier}",
            payload={"mobileNumber": prepaid_mobile},
        )
        assert resp.error is None

    def test_plan_data_present(self, client, prepaid_mobile, plan_identifier):
        resp = client.post(
            f"/gw/v1/bbps/prepaid/plans/{plan_identifier}",
            payload={"mobileNumber": prepaid_mobile},
        )
        assert resp.data is not None, "Plan data is null"

    def test_plan_has_denomination(self, client, prepaid_mobile, plan_identifier):
        resp = client.post(
            f"/gw/v1/bbps/prepaid/plans/{plan_identifier}",
            payload={"mobileNumber": prepaid_mobile},
        )
        assert resp.ok
        plan = resp.data
        assert plan.get("denomination") is not None, "Plan missing denomination"

    def test_plan_denomination_is_positive(self, client, prepaid_mobile, plan_identifier):
        resp = client.post(
            f"/gw/v1/bbps/prepaid/plans/{plan_identifier}",
            payload={"mobileNumber": prepaid_mobile},
        )
        assert resp.ok
        denomination = resp.data.get("denomination")
        if denomination is not None:
            assert float(denomination) > 0, f"Plan denomination should be positive: {denomination}"


@pytest.mark.bbps
@pytest.mark.prepaid
class TestPrepaidOperatorFields:
    """Validates extended fields for prepaid operators."""

    def test_operator_codes_are_non_empty_strings(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/operators")
        assert resp.ok
        for op in resp.data or []:
            assert isinstance(op["operatorCode"], str)
            assert len(op["operatorCode"]) > 0

    def test_operator_names_are_non_empty_strings(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/operators")
        assert resp.ok
        for op in resp.data or []:
            assert isinstance(op["operatorName"], str)
            assert len(op["operatorName"]) > 0

    def test_no_duplicate_operator_codes(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/operators")
        assert resp.ok
        codes = [op["operatorCode"] for op in (resp.data or [])]
        assert len(codes) == len(set(codes)), "Duplicate operatorCode values found"


@pytest.mark.bbps
@pytest.mark.prepaid
class TestPrepaidCircleFields:
    """Validates extended fields for prepaid circles."""

    def test_circle_ref_ids_are_non_empty(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/circles")
        assert resp.ok
        for circle in resp.data or []:
            assert len(circle["circleRefId"]) > 0

    def test_circle_names_are_non_empty(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/circles")
        assert resp.ok
        for circle in resp.data or []:
            assert len(circle["circleName"]) > 0

    def test_no_duplicate_circle_ref_ids(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/circles")
        assert resp.ok
        ids = [c["circleRefId"] for c in (resp.data or [])]
        assert len(ids) == len(set(ids)), "Duplicate circleRefId values found"

    def test_known_circles_present(self, client):
        resp = client.get("/gw/v1/bbps/prepaid/circles")
        assert resp.ok
        names = {c["circleName"].upper() for c in (resp.data or [])}
        known = {"DELHI", "MUMBAI", "MAHARASHTRA", "KARNATAKA"}
        found = known & names
        assert found, f"No known circles found. Got: {names}"

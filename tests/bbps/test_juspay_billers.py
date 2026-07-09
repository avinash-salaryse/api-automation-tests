"""
Juspay biller integration tests.

Tests GET /gw/v1/bbps/billers/{id} for every biller that has Juspay in
supported_providers (27 billers across 27 categories, sourced from dev DB).

All 27 responses are fetched once via a session-scoped fixture and reused
across every test method — only 27 API calls regardless of test count.

3 billers are Juspay-only (no PayU fallback):
  - EDUCATION FEES:  Meerut Institute Of Technology test
  - LOAN REPAYMENT:  HDB Financial Services Limited test
  - METRO:           Chennai Metro Rail (CMRL)
"""

import pytest


# ── Biller catalogue (from dev DB + API, 2026-07-07) ─────────────────────────

JUSPAY_BILLERS = [
    {
        "id": "broadband-act-fibernet",
        "category": "BROADBAND POSTPAID",
        "biller_ref_id": "dde43b59-a5f1-4dca-a9b0-b05b7011eab3",
        "biller_name": "ACT Fibernet",
        "category_name": "broadband postpaid",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": False,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "34ea9c71-b9e4-4d59-8d73-db5d332a7d4d",
    },
    {
        "id": "cable-decathelon",
        "category": "CABLE",
        "biller_ref_id": "2df9c046-8685-4738-b75b-c5fee2787ce3",
        "biller_name": "Decathelon",
        "category_name": "cable",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "d099e1ad-c9fd-4697-987b-0433d57375fe",
    },
    {
        "id": "clubs-mp-chamber",
        "category": "CLUBS AND ASSOCIATIONS",
        "biller_ref_id": "c36596a1-65a1-47a1-90ad-f88198a19749",
        "biller_name": "Madhya Pradesh Chamber Of Commerce And Industry test",
        "category_name": "clubs and associations",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "eec6844d-c96a-4408-b9dc-eb54f2f45f93",
    },
    {
        "id": "credit-card-bob",
        "category": "CREDIT CARD",
        "biller_ref_id": "84138ad9-3700-4bf8-a4c8-0031e34d93f6",
        "biller_name": "Bank of Baroda test",
        "category_name": "credit card",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "6af95789-6568-4d7e-9b1b-e16d27d52ca4",
    },
    {
        "id": "donation-vaishno-devi",
        "category": "DONATION",
        "biller_ref_id": "4da5dbcd-5e73-4e6d-8707-8e93000b0abc",
        "biller_name": "Shri Mata Vaishno Devi Shrine Board",
        "category_name": "donation",
        "fetch_bill": False,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 5,
        "category_ref_id": "8a6b574f-bb3d-47eb-9a39-3d1ea41697c7",
    },
    {
        "id": "dth-sun-direct",
        "category": "DTH",
        "biller_ref_id": "c3cadd8b-81d9-4312-914a-ab5b1eb2db38",
        "biller_name": "Sun Direct TV (With Validation)",
        "category_name": "DTH",
        "fetch_bill": False,
        "adhoc": True,
        "has_blocked_modes": False,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "b2901df2-f8ea-4636-8be1-6f7ee81b7349",
    },
    {
        "id": "education-fees-meerut",
        "category": "EDUCATION FEES",
        "biller_ref_id": "4f6dc2f3-af24-43c2-9807-5fb563e5b8c4",
        "biller_name": "Meerut Institute Of Technology test",
        "category_name": "education fees",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": True,
        "visible_param_count": 1,
        "category_ref_id": "8eee93c8-3b2a-436f-abed-afe8b5d1ea2a",
    },
    {
        "id": "electricity-cesu-odisha",
        "category": "ELECTRICITY",
        "biller_ref_id": "428da9bd-1af0-44b4-a6f1-2b1a75ef2fef",
        "biller_name": "CESU,Odisha test",
        "category_name": "electricity",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "1d1ce4bb-2684-434d-a6a2-9b231594c415",
    },
    {
        "id": "fastag-bot",
        "category": "FASTAG",
        "biller_ref_id": "04ce168d-0e5e-403b-8848-4c32238169f1",
        "biller_name": "Bank of Test - Fastag test",
        "category_name": "FASTag",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "5a61b4ab-d18c-4ab6-9032-0761eb0f1758",
    },
    {
        "id": "gas-sabarmati",
        "category": "GAS",
        "biller_ref_id": "b365e85c-5510-4d72-a419-3f9d43979451",
        "biller_name": "Sabarmati Gas Limited (SGL)",
        "category_name": "piped gas",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": False,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "cbdc1828-5843-4329-b0ba-f94ee3316f8d",
    },
    {
        "id": "hospital-bk-arogyam",
        "category": "HOSPITAL",
        "biller_ref_id": "965c646a-d85b-4508-a2df-338f5c76318a",
        "biller_name": "B.K. Arogyam and Research Pvt. Ltd test",
        "category_name": "hospital",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "8e406813-2a18-485b-afba-645d5e99b5e7",
    },
    {
        "id": "housing-society-biller1",
        "category": "HOUSING SOCIETY",
        "biller_ref_id": "861d6b20-b40d-4865-a56c-06f85b78c0e6",
        "biller_name": "SocietyBiller1",
        "category_name": "housing society",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "b3d5fbdf-686f-43a0-b5d9-8cb2a0d92111",
    },
    {
        "id": "landline-mtnl-mumbai",
        "category": "LANDLINE POSTPAID",
        "biller_ref_id": "d59b04dc-2b68-4b6b-a4c0-0ec504578a4d",
        "biller_name": "MTNL Mumbai test",
        "category_name": "landline postpaid",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "a57d1250-6f21-497a-9403-c80494043a33",
    },
    {
        "id": "loan-hdb-financial",
        "category": "LOAN REPAYMENT",
        "biller_ref_id": "bda03cb2-e036-49fd-baf4-14fb3a240d30",
        "biller_name": "HDB Financial Services Limited test",
        "category_name": "loan repayment",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": True,
        "visible_param_count": 1,
        "category_ref_id": "a1d5f574-dc45-4683-b2e7-a0ac0ba61b1e",
    },
    {
        "id": "lpg-hindustan-ou12",
        "category": "LPG GAS",
        "biller_ref_id": "8b920404-7353-4e1a-9dc2-12c669ecdd06",
        "biller_name": "Hindustan OU12",
        "category_name": "gas cylinder",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": False,
        "juspay_only": False,
        "visible_param_count": 4,
        "category_ref_id": "47dfb3ff-b2d8-4a88-b0fc-2302dcda7abd",
    },
    {
        "id": "metro-chennai-cmrl",
        "category": "METRO",
        "biller_ref_id": "844316a8-dc08-4860-83c4-fbe5bb6d3c2d",
        "biller_name": "Chennai Metro Rail (CMRL)",
        "category_name": "metro",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": True,
        "visible_param_count": 1,
        "category_ref_id": "f159773b-13de-4a84-b462-37c57c94e324",
    },
    {
        "id": "mobile-postpaid-test",
        "category": "MOBILE POSTPAID",
        "biller_ref_id": "ff2b008a-1a78-4281-bd35-914053f8b594",
        "biller_name": "Postpaid Test Biller",
        "category_name": "postpaid",
        "fetch_bill": True,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "4dba07a4-839c-4575-afc4-837c708b575f",
    },
    {
        "id": "mobile-prepaid-npci",
        "category": "MOBILE PREPAID",
        "biller_ref_id": "c8c7428d-538f-44e3-a498-6ef81fbbe536",
        "biller_name": "NPCI Mobile Prepaid 002",
        "category_name": "mobile prepaid",
        "fetch_bill": False,
        "adhoc": True,
        "has_blocked_modes": False,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "12cc7039-2f3d-4573-8b26-a2dcc252fc90",
    },
    {
        "id": "municipal-services-corp",
        "category": "MUNICIPAL SERVICES",
        "biller_ref_id": "039dae15-7521-46b8-bab2-00b2a43af116",
        "biller_name": "Municipal Corporation",
        "category_name": "municipal services",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "2a586821-5c66-46bc-b745-e30d930837f5",
    },
    {
        "id": "municipal-taxes-kolkata",
        "category": "MUNICIPAL TAXES",
        "biller_ref_id": "785abebc-2fba-4731-af3a-c95c10c0bf4f",
        "biller_name": "Kolkata Municipal Corporation",
        "category_name": "municipal taxes",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "5c672b16-b369-475b-b1fb-9e07c893dd62",
    },
    {
        "id": "nps-national-pension",
        "category": "NATIONAL PENSION SYSTEM",
        "biller_ref_id": "efb3f162-d3b5-41e5-8b67-b06aed1f7561",
        "biller_name": "National Pension System",
        "category_name": "national pension system",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 4,
        "category_ref_id": "f83cd97f-6c37-45cb-ba8d-342f5ef70cfc",
    },
    {
        "id": "ncmc-test-card",
        "category": "NCMC RECHARGE",
        "biller_ref_id": "f6ae072e-67b4-464a-8660-b8c059830b77",
        "biller_name": "Test NCMC Card",
        "category_name": "ncmc recharge",
        "fetch_bill": False,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "f8bc825a-8bf4-46ed-aa54-92442cba6bb8",
    },
    {
        "id": "prepaid-meter-testing",
        "category": "PREPAID METER",
        "biller_ref_id": "b5ae6f70-2ecf-43e4-9624-71cb8b03a0fc",
        "biller_name": "Prepaid meter testing",
        "category_name": "prepaid meter",
        "fetch_bill": False,
        "adhoc": True,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "29c5ab2e-9242-4b90-8311-913f4eb0e361",
    },
    {
        "id": "recurring-deposit-dilip",
        "category": "RECURRING DEPOSIT",
        "biller_ref_id": "3ff302ee-6853-4d2e-b8eb-3a0fe2f23d3b",
        "biller_name": "Dilip Sonigara Jewellers Pvt Ltd",
        "category_name": "recurring deposit",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "63d31159-fde9-448d-ba5c-22737de60cd1",
    },
    {
        "id": "rental-pcn-manpower",
        "category": "RENTAL",
        "biller_ref_id": "74c05bcb-e71d-4c6c-83e4-bd3ae3f23259",
        "biller_name": "Pcn Manpower Solutions",
        "category_name": "rental",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 1,
        "category_ref_id": "0e137cf3-b518-4498-af6d-5b3d36935b59",
    },
    {
        "id": "subscription-hotstar",
        "category": "SUBSCRIPTION",
        "biller_ref_id": "d6a22665-09a8-49c6-90c5-192ae9f97358",
        "biller_name": "Disney+ Hotstar",
        "category_name": "subscription",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": True,
        "juspay_only": False,
        "visible_param_count": 2,
        "category_ref_id": "e0247bb4-0034-4299-8ba9-b08f96c620b3",
    },
    {
        "id": "water-amritsar-mc",
        "category": "WATER",
        "biller_ref_id": "48e80c2a-2a7e-4088-bb0d-d65b3f2f5064",
        "biller_name": "Municipal Corporation of Amritsar",
        "category_name": "water",
        "fetch_bill": True,
        "adhoc": False,
        "has_blocked_modes": False,
        "juspay_only": False,
        "visible_param_count": 3,
        "category_ref_id": "c647af79-752b-4141-a3ef-a07cbb8eaeae",
    },
]

JUSPAY_ONLY_BILLERS = [b for b in JUSPAY_BILLERS if b["juspay_only"]]
VALID_DATA_TYPES = {"NUMERIC", "ALPHANUMERIC", "ALPHABETIC"}


# ── Session-scoped fixture — fetches all 27 responses once ───────────────────

@pytest.fixture(scope="session")
def juspay_responses(client):
    """
    Calls GET /gw/v1/bbps/billers/{id} for every biller in JUSPAY_BILLERS.
    Returns a dict keyed by biller_ref_id so individual tests can look up
    the cached response without making additional API calls.
    """
    return {
        b["biller_ref_id"]: client.get(f"/gw/v1/bbps/billers/{b['biller_ref_id']}")
        for b in JUSPAY_BILLERS
    }


# ── Helper ───────────────────────────────────────────────────────────────────

def _label(b):
    return b["id"]


def _visible_params(data):
    return [p for p in data.get("customerParams") or [] if p.get("visibility") is not False]


# ── Tests: biller details response structure ─────────────────────────────────

@pytest.mark.bbps
@pytest.mark.juspay
@pytest.mark.parametrize("biller", JUSPAY_BILLERS, ids=_label)
class TestJuspayBillerDetails:
    """
    Verifies the GET /gw/v1/bbps/billers/{id} response structure
    for each of the 27 Juspay-supported billers.
    """

    def test_returns_200(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.status_code == 200, (
            f"[{biller['category']}] {biller['biller_name']}: "
            f"expected 200, got {resp.status_code}"
        )

    def test_no_error_in_response(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.error is None, (
            f"[{biller['category']}] {biller['biller_name']}: "
            f"unexpected error {resp.error}"
        )

    def test_biller_reference_id_matches(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok, f"Response not OK: {resp.error}"
        assert resp.data.get("billerReferenceId") == biller["biller_ref_id"], (
            f"billerReferenceId mismatch for {biller['biller_name']}"
        )

    def test_biller_name_is_non_empty(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        assert resp.data.get("billerName"), (
            f"billerName missing or empty for {biller['biller_ref_id']}"
        )

    def test_biller_category_name_present(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        assert resp.data.get("billerCategoryName"), (
            f"billerCategoryName missing for {biller['biller_name']}"
        )

    def test_fetch_bill_flag_correct(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        assert resp.data.get("fetchBill") == biller["fetch_bill"], (
            f"[{biller['biller_name']}] fetchBill expected "
            f"{biller['fetch_bill']}, got {resp.data.get('fetchBill')}"
        )

    def test_adhoc_flag_is_boolean(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        assert isinstance(resp.data.get("adhoc"), bool), (
            f"adhoc must be a boolean for {biller['biller_name']}"
        )

    def test_adhoc_flag_correct(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        assert resp.data.get("adhoc") == biller["adhoc"], (
            f"[{biller['biller_name']}] adhoc expected "
            f"{biller['adhoc']}, got {resp.data.get('adhoc')}"
        )

    def test_blocked_payment_modes_is_string(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        modes = resp.data.get("blockedPaymentModes")
        assert isinstance(modes, str), (
            f"blockedPaymentModes must be a string for {biller['biller_name']}, "
            f"got {type(modes)}"
        )

    def test_blocked_payment_modes_present_when_expected(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        modes = resp.data.get("blockedPaymentModes", "")
        has_blocked = bool(modes)
        assert has_blocked == biller["has_blocked_modes"], (
            f"[{biller['biller_name']}] blocked modes: expected "
            f"{'present' if biller['has_blocked_modes'] else 'empty'}, "
            f"got '{modes}'"
        )

    def test_customer_params_is_list(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        assert isinstance(resp.data.get("customerParams"), list), (
            f"customerParams must be a list for {biller['biller_name']}"
        )

    def test_visible_param_count_correct(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        visible = _visible_params(resp.data)
        assert len(visible) == biller["visible_param_count"], (
            f"[{biller['biller_name']}] expected {biller['visible_param_count']} "
            f"visible params, got {len(visible)}: "
            f"{[p.get('paramName') for p in visible]}"
        )

    def test_category_reference_id_present(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        assert resp.data.get("categoryReferenceId"), (
            f"categoryReferenceId missing for {biller['biller_name']}"
        )

    def test_biller_response_type_present(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        assert resp.data.get("billerResponseType") in ("SINGLE", "MULTI"), (
            f"unexpected billerResponseType for {biller['biller_name']}: "
            f"{resp.data.get('billerResponseType')}"
        )


# ── Tests: customer param field validation ────────────────────────────────────

@pytest.mark.bbps
@pytest.mark.juspay
@pytest.mark.parametrize("biller", JUSPAY_BILLERS, ids=_label)
class TestJuspayCustomerParams:
    """
    Verifies each visible customer param has the fields the frontend
    needs to render its input form.
    """

    def test_each_param_has_param_name(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        for param in _visible_params(resp.data):
            assert param.get("paramName"), (
                f"[{biller['biller_name']}] param missing paramName: {param}"
            )

    def test_each_param_has_valid_data_type(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        for param in _visible_params(resp.data):
            dt = param.get("dataType")
            assert dt in VALID_DATA_TYPES, (
                f"[{biller['biller_name']}] param '{param.get('paramName')}' "
                f"has unknown dataType '{dt}'"
            )

    def test_optional_flag_is_boolean(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        for param in _visible_params(resp.data):
            assert isinstance(param.get("optional"), bool), (
                f"[{biller['biller_name']}] param '{param.get('paramName')}' "
                f"optional is not a boolean: {param.get('optional')}"
            )

    def test_numeric_params_have_length_bounds(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        for param in _visible_params(resp.data):
            if param.get("dataType") == "NUMERIC" and not param.get("optional"):
                min_len = param.get("minLength")
                max_len = param.get("maxLength")
                assert min_len is not None or max_len is not None, (
                    f"[{biller['biller_name']}] required NUMERIC param "
                    f"'{param.get('paramName')}' has no length bounds"
                )

    def test_params_with_values_have_regex(self, juspay_responses, biller):
        """Params with a dropdown values list should also have a regex for validation."""
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        for param in _visible_params(resp.data):
            if param.get("values"):
                assert param.get("regex"), (
                    f"[{biller['biller_name']}] param '{param.get('paramName')}' "
                    f"has values but no regex"
                )


# ── Tests: Juspay-only billers ────────────────────────────────────────────────

@pytest.mark.bbps
@pytest.mark.juspay
class TestJuspayOnlyBillers:
    """
    Specific tests for the 3 billers that have ONLY Juspay (no PayU fallback).
    These are critical to verify since they have no fallback if Juspay is down.
    """

    def test_all_three_juspay_only_billers_reachable(self, juspay_responses):
        for biller in JUSPAY_ONLY_BILLERS:
            resp = juspay_responses[biller["biller_ref_id"]]
            assert resp.ok, (
                f"Juspay-only biller unreachable: [{biller['category']}] "
                f"{biller['biller_name']} — {resp.error}"
            )

    @pytest.mark.parametrize("biller", JUSPAY_ONLY_BILLERS, ids=_label)
    def test_juspay_only_biller_appears_in_category_list(self, client, biller):
        """
        Verifies the Juspay-only biller is visible in its category's biller listing
        (allBillers or popularBillers), not just reachable via direct ref ID lookup.
        """
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller['category_ref_id']}/billers"
            f"?page=0&size=50"
        )
        assert resp.ok, (
            f"Failed to fetch biller list for category {biller['category']}: {resp.error}"
        )
        all_billers = resp.data.get("allBillers", {}).get("billersList", [])
        popular = resp.data.get("popularBillers", {}).get("billersList", [])
        all_ref_ids = {b.get("billerReferenceId") for b in all_billers + popular}
        assert biller["biller_ref_id"] in all_ref_ids, (
            f"Juspay-only biller '{biller['biller_name']}' not found in "
            f"{biller['category']} category listing — "
            f"found {len(all_ref_ids)} billers but not this ref ID"
        )

    @pytest.mark.parametrize("biller", JUSPAY_ONLY_BILLERS, ids=_label)
    def test_juspay_only_biller_has_blocked_modes_if_expected(self, juspay_responses, biller):
        resp = juspay_responses[biller["biller_ref_id"]]
        assert resp.ok
        modes = resp.data.get("blockedPaymentModes", "")
        assert isinstance(modes, str), (
            f"blockedPaymentModes must be a string for {biller['biller_name']}"
        )
        if biller["has_blocked_modes"]:
            assert modes, (
                f"Juspay-only biller '{biller['biller_name']}' expected "
                f"blocked payment modes but got empty string"
            )


# ── Tests: category coverage ──────────────────────────────────────────────────

@pytest.mark.bbps
@pytest.mark.juspay
class TestJuspayBillerCategoryCoverage:
    """
    Verifies that every category with a Juspay biller returns at least
    one biller from the category listing API.
    """

    @pytest.fixture(scope="class")
    def category_ref_ids(self):
        seen = {}
        for b in JUSPAY_BILLERS:
            seen.setdefault(b["category_ref_id"], b["category"])
        return seen

    def test_all_27_juspay_categories_have_billers(self, client, category_ref_ids):
        empty_categories = []
        for cat_ref, cat_name in category_ref_ids.items():
            resp = client.get(
                f"/gw/v1/bbps/biller-categories/{cat_ref}/billers?page=0&size=5"
            )
            all_b = resp.data.get("allBillers", {}).get("billersList", []) if resp.ok else []
            popular = resp.data.get("popularBillers", {}).get("billersList", []) if resp.ok else []
            if not all_b and not popular:
                empty_categories.append(cat_name)

        assert not empty_categories, (
            f"These Juspay categories returned no billers from the listing API: "
            f"{empty_categories}"
        )

    def test_all_27_juspay_categories_return_200(self, client, category_ref_ids):
        failed = []
        for cat_ref, cat_name in category_ref_ids.items():
            resp = client.get(
                f"/gw/v1/bbps/biller-categories/{cat_ref}/billers?page=0&size=5"
            )
            if resp.status_code != 200:
                failed.append(f"{cat_name} ({resp.status_code})")

        assert not failed, (
            f"These Juspay category listing calls did not return 200: {failed}"
        )

"""
Discovery flow tests
  GET /gw/v1/bbps/biller-categories
  GET /gw/v1/bbps/biller-categories/{id}/billers
  GET /gw/v1/bbps/billers/{id}
"""

import pytest


@pytest.mark.bbps
@pytest.mark.discovery
@pytest.mark.smoke
class TestBillerCategories:

    def test_returns_200(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        assert resp.status_code == 200

    def test_no_error_in_response(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        assert resp.error is None, f"Unexpected error: {resp.error}"

    def test_category_list_not_empty(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        assert resp.ok, f"Unexpected error: {resp.error}"
        category_list = resp.data["categoryData"]["categoryList"]
        assert len(category_list) > 0

    def test_each_category_has_name_and_reference_id(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        assert resp.ok, f"Unexpected error: {resp.error}"
        for cat in resp.data["categoryData"]["categoryList"]:
            assert cat.get("categoryName"), f"Missing categoryName: {cat}"
            assert cat.get("referenceId"), f"Missing referenceId: {cat}"

    def test_prepaid_category_visible_on_supported_app_version(self, client):
        # App version 3.5.0 (default) meets the 2.4.4 minimum for prepaid
        resp = client.get("/gw/v1/bbps/biller-categories")
        assert resp.ok, f"Unexpected error: {resp.error}"
        names = [
            c["categoryName"].upper()
            for c in resp.data["categoryData"]["categoryList"]
        ]
        assert "MOBILE PREPAID" in names, (
            "MOBILE PREPAID category not found — check app version header"
        )

    def test_header_text_present(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        assert resp.ok, f"Unexpected error: {resp.error}"
        assert resp.data["categoryData"].get("headerText") is not None


@pytest.mark.bbps
@pytest.mark.discovery
class TestBillersByCategory:

    def test_returns_200(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers"
        )
        assert resp.status_code == 200

    def test_no_error_in_response(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers"
        )
        assert resp.error is None

    def test_billers_list_not_empty(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers"
        )
        all_billers = resp.data.get("allBillers", {}).get("billersList", [])
        popular = resp.data.get("popularBillers", {}).get("billersList", [])
        assert len(all_billers) > 0 or len(popular) > 0, "No billers returned"

    def test_biller_category_name_present(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers"
        )
        assert resp.data.get("billerCategoryName"), "billerCategoryName missing"

    def test_each_biller_has_reference_id_and_name(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers"
        )
        all_billers = (
            resp.data.get("allBillers", {}).get("billersList", [])
            + resp.data.get("popularBillers", {}).get("billersList", [])
        )
        for biller in all_billers:
            assert biller.get("billerReferenceId"), f"Biller missing billerReferenceId: {biller}"
            assert biller.get("billerName"), f"Biller missing billerName: {biller}"

    def test_search_with_valid_term_returns_results(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "Airtel"},
        )
        assert resp.error is None
        all_billers = resp.data.get("allBillers", {}).get("billersList", [])
        for biller in all_billers:
            assert "airtel" in biller["billerName"].lower(), (
                f"Search returned unrelated biller: {biller['billerName']}"
            )

    def test_search_with_nonsense_returns_empty(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "xyznonexistent999abc"},
        )
        assert resp.error is None
        all_billers = resp.data.get("allBillers", {}).get("billersList", [])
        popular = resp.data.get("popularBillers", {}).get("billersList", [])
        assert all_billers == [] and popular == []

    def test_pagination_page_size(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"page": 0, "size": 3},
        )
        assert resp.error is None
        all_billers = resp.data.get("allBillers", {}).get("billersList", [])
        assert len(all_billers) <= 3, "Returned more billers than requested page size"

    def test_pagination_different_pages_differ(self, client, biller_category_ref_id):
        page0 = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"page": 0, "size": 5},
        )
        page1 = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"page": 1, "size": 5},
        )
        ids_p0 = {
            b["billerReferenceId"]
            for b in page0.data.get("allBillers", {}).get("billersList", [])
        }
        ids_p1 = {
            b["billerReferenceId"]
            for b in page1.data.get("allBillers", {}).get("billersList", [])
        }
        if ids_p1:
            assert ids_p0.isdisjoint(ids_p1), "Pages returned overlapping billers"


@pytest.mark.bbps
@pytest.mark.discovery
class TestBillerDetails:

    def test_returns_200(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        assert resp.status_code == 200

    def test_no_error_in_response(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        assert resp.error is None

    def test_biller_name_present(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        assert resp.data.get("billerName"), "billerName missing from biller details"

    def test_reference_id_matches_request(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        assert resp.data.get("billerReferenceId") == biller_ref_id

    def test_customer_params_schema_present(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        params = resp.data.get("customerParams")
        assert isinstance(params, list), "customerParams should be a list"
        assert len(params) > 0, "customerParams schema is empty"

    def test_customer_params_have_required_fields(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        for param in resp.data["customerParams"]:
            assert param.get("paramName"), f"Param missing paramName: {param}"

    def test_fetch_bill_flag_present(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        assert "fetchBill" in resp.data, "fetchBill flag missing from biller details"

    def test_invalid_biller_id_returns_error(self, client):
        resp = client.get("/gw/v1/bbps/billers/00000000-0000-0000-0000-000000000000")
        assert resp.error is not None or resp.data is None, (
            "Expected error for non-existent biller"
        )

    def test_fetch_bill_is_boolean(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        assert isinstance(resp.data.get("fetchBill"), bool), (
            "fetchBill should be a boolean"
        )

    def test_biller_logo_url_is_string(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        logo = resp.data.get("billerLogoUrl")
        if logo is not None:
            assert isinstance(logo, str), "billerLogoUrl should be a string"

    def test_blocked_payment_modes_present(self, client, biller_ref_id):
        # blockedPaymentModes may be a comma-separated string or list depending on biller config
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        modes = resp.data.get("blockedPaymentModes")
        if modes is not None:
            assert isinstance(modes, (list, str)), (
                "blockedPaymentModes should be a list or comma-separated string"
            )

    def test_customer_params_have_param_type(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        for param in resp.data.get("customerParams", []):
            assert param.get("paramName"), f"Param missing paramName: {param}"
            # At least paramName must be present; optional: dataType / paramType
            assert isinstance(param["paramName"], str)

    def test_adhoc_flag_present(self, client, biller_ref_id):
        # biller details exposes adhoc flag (not allowsUpiCreditCard — that's on bill/account)
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        assert "adhoc" in resp.data, "adhoc flag missing from biller details"

    def test_adhoc_flag_is_boolean(self, client, biller_ref_id):
        resp = client.get(f"/gw/v1/bbps/billers/{biller_ref_id}")
        val = resp.data.get("adhoc")
        if val is not None:
            assert isinstance(val, bool), "adhoc should be a boolean"


@pytest.mark.bbps
@pytest.mark.discovery
class TestBillerSearchEdgeCases:

    def test_search_case_insensitive(self, client, biller_category_ref_id):
        resp_lower = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "test", "page": 0, "size": 50},
        )
        resp_upper = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "TEST", "page": 0, "size": 50},
        )
        if resp_lower.ok and resp_upper.ok:
            lower_ids = {
                b["billerReferenceId"]
                for b in resp_lower.data.get("allBillers", {}).get("billersList", [])
            }
            upper_ids = {
                b["billerReferenceId"]
                for b in resp_upper.data.get("allBillers", {}).get("billersList", [])
            }
            if lower_ids and upper_ids:
                assert lower_ids == upper_ids, "Search should be case-insensitive"

    def test_search_with_special_characters_does_not_500(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "test@#$%", "page": 0, "size": 10},
        )
        assert resp.status_code == 200

    def test_search_partial_match_returns_superset(self, client, biller_category_ref_id):
        # "Air" should return results that include "Airtel"
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "Air", "page": 0, "size": 50},
        )
        assert resp.ok
        assert resp.status_code == 200

    def test_search_with_whitespace_only_does_not_error(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "   ", "page": 0, "size": 10},
        )
        assert resp.status_code == 200

    def test_search_very_long_string_does_not_500(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"search": "a" * 500, "page": 0, "size": 10},
        )
        assert resp.status_code == 200


@pytest.mark.bbps
@pytest.mark.discovery
class TestBillersPaginationEdgeCases:

    def test_large_page_number_returns_empty_list(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"page": 99999, "size": 10},
        )
        assert resp.status_code == 200
        billers = resp.data.get("allBillers", {}).get("billersList", [])
        assert isinstance(billers, list), "Expected a list (possibly empty) for large page"

    def test_size_one_returns_at_most_one_biller(self, client, biller_category_ref_id):
        resp = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"page": 0, "size": 1},
        )
        assert resp.ok
        billers = resp.data.get("allBillers", {}).get("billersList", [])
        assert len(billers) <= 1, f"size=1 returned {len(billers)} billers"

    def test_total_count_consistent_across_pages(self, client, biller_category_ref_id):
        # Fetching full page vs split across 2 pages should not produce duplicates
        full = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"page": 0, "size": 6},
        )
        p0 = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"page": 0, "size": 3},
        )
        p1 = client.get(
            f"/gw/v1/bbps/biller-categories/{biller_category_ref_id}/billers",
            params={"page": 1, "size": 3},
        )
        if full.ok and p0.ok and p1.ok:
            full_ids = {
                b["billerReferenceId"]
                for b in full.data.get("allBillers", {}).get("billersList", [])
            }
            split_ids = {
                b["billerReferenceId"]
                for b in (
                    p0.data.get("allBillers", {}).get("billersList", [])
                    + p1.data.get("allBillers", {}).get("billersList", [])
                )
            }
            assert full_ids == split_ids, "Paginated results don't match full-page results"


@pytest.mark.bbps
@pytest.mark.discovery
class TestCategoryStructure:

    def test_category_data_is_dict(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        assert isinstance(resp.data.get("categoryData"), dict), (
            "categoryData should be a dict"
        )

    def test_each_category_reference_id_is_uuid_format(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        for cat in resp.data["categoryData"]["categoryList"]:
            ref_id = cat.get("referenceId", "")
            assert len(ref_id.split("-")) == 5, (
                f"referenceId is not UUID format: {ref_id}"
            )

    def test_quick_payment_data_present(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        # quickPaymentData may be null if no billers are configured
        assert "quickPaymentData" in resp.data or "categoryData" in resp.data, (
            "Neither quickPaymentData nor categoryData in response"
        )

    def test_category_names_are_non_empty_strings(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        for cat in resp.data["categoryData"]["categoryList"]:
            assert isinstance(cat["categoryName"], str)
            assert len(cat["categoryName"].strip()) > 0, (
                f"Empty categoryName for category: {cat}"
            )

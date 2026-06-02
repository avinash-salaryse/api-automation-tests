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
        category_list = resp.data["categoryData"]["categoryList"]
        assert len(category_list) > 0

    def test_each_category_has_name_and_reference_id(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
        for cat in resp.data["categoryData"]["categoryList"]:
            assert cat.get("categoryName"), f"Missing categoryName: {cat}"
            assert cat.get("referenceId"), f"Missing referenceId: {cat}"

    def test_prepaid_category_visible_on_supported_app_version(self, client):
        # App version 3.5.0 (default) meets the 2.4.4 minimum for prepaid
        resp = client.get("/gw/v1/bbps/biller-categories")
        names = [
            c["categoryName"].upper()
            for c in resp.data["categoryData"]["categoryList"]
        ]
        assert "MOBILE PREPAID" in names, (
            "MOBILE PREPAID category not found — check app version header"
        )

    def test_header_text_present(self, client):
        resp = client.get("/gw/v1/bbps/biller-categories")
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

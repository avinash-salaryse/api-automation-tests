from __future__ import annotations

from typing import Optional

import requests

from config import settings


class ApiResponse:
    """Thin wrapper around requests.Response for clean test assertions."""

    def __init__(self, response: requests.Response):
        self._response = response
        try:
            self._body: dict = response.json()
        except ValueError:
            self._body = {}

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def data(self):
        return self._body.get("data")

    @property
    def error(self) -> Optional[dict]:
        err = self._body.get("error")
        if err is None:
            return None
        if isinstance(err, dict):
            return err
        # Spring Boot 400 error format: {"error": "Bad Request", "message": "...", ...}
        return {"errorReason": str(err), "errorReasonText": self._body.get("message", str(err))}

    @property
    def error_reason(self) -> Optional[str]:
        return (self.error or {}).get("errorReason")

    @property
    def error_text(self) -> Optional[str]:
        return (self.error or {}).get("errorReasonText")

    @property
    def ok(self) -> bool:
        """True when HTTP is 2xx and the response body has no error."""
        return self._response.ok and self.error is None

    def __repr__(self) -> str:
        return f"ApiResponse(status={self.status_code}, error={self.error})"


class SalarySeClient:
    """HTTP client for the SalarySe gateway API."""

    def __init__(self, token: str):
        self._session = requests.Session()
        self._session.headers.update(
            {
                "x-token": token,
                "Content-Type": "application/json",
                "x-os": settings.OS,
                "x-app-version": settings.APP_VERSION,
                "x-device-id": settings.DEVICE_ID,
            }
        )

    # ── HTTP verbs ─────────────────────────────────────────────────────────────

    def get(self, path: str, params: dict = None) -> ApiResponse:
        return self._call("GET", path, params=params)

    def post(self, path: str, payload: dict = None) -> ApiResponse:
        return self._call("POST", path, json=payload or {})

    # ── Internal ───────────────────────────────────────────────────────────────

    def _call(self, method: str, path: str, **kwargs) -> ApiResponse:
        url = f"{settings.BASE_URL}{path}"
        response = self._session.request(method, url, **kwargs)
        return ApiResponse(response)

    # ── Factory ────────────────────────────────────────────────────────────────

    @classmethod
    def from_env(cls) -> SalarySeClient:
        """
        Build an authenticated client from environment variables.
        Performs phone + OTP login (dev OTP is fixed at 123456).
        """
        if not settings.TEST_PHONE:
            raise EnvironmentError("TEST_PHONE must be set in .env")
        token = cls._login(settings.TEST_PHONE, settings.TEST_OTP)
        return cls(token)

    @staticmethod
    def _login(phone: str, otp: str) -> str:
        """Trigger OTP then validate it; return the auth token string."""
        headers = {
            "Content-Type": "application/json",
            "x-device-id": settings.DEVICE_ID,
            "x-os": settings.OS,
            "x-app-version": settings.APP_VERSION,
        }
        base = settings.BASE_URL

        # Step 1 — request OTP (fire-and-forget; dev OTP is fixed)
        requests.post(f"{base}/gw/v1/login", json={"phone": phone}, headers=headers)

        # Step 2 — validate OTP → receive AuthToken
        resp = requests.post(
            f"{base}/gw/v1/validate_otp",
            json={"phone": phone, "otp": otp},
            headers=headers,
        )
        resp.raise_for_status()
        body = resp.json()
        token_data: dict = body.get("data") or {}
        token = token_data.get("token") or token_data.get("accessToken")
        if not token:
            raise ValueError(f"Login failed — could not extract token from: {body}")
        return token

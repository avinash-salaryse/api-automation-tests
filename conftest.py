import pytest

from config import settings
from utils.api_client import SalarySeClient

_ALLOWED_ENVS = {"dev", "local"}


def pytest_configure(config):
    if settings.ENV not in _ALLOWED_ENVS:
        raise SystemExit(
            f"[SAFETY] Tests are only allowed on dev or local environments. "
            f"Current ENV='{settings.ENV}'. Set ENV=dev or ENV=local in your .env to proceed."
        )


@pytest.fixture(scope="session")
def client() -> SalarySeClient:
    """
    Session-scoped authenticated client.
    Logs in once via phone + OTP at the start of the test run.
    """
    return SalarySeClient.from_env()

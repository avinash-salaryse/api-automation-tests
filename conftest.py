import pytest

from utils.api_client import SalarySeClient


@pytest.fixture(scope="session")
def client() -> SalarySeClient:
    """
    Session-scoped authenticated client.
    Logs in once via phone + OTP at the start of the test run.
    """
    return SalarySeClient.from_env()

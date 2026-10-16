"""All application HTTP in tests must be explicitly mocked."""

import pytest
import requests


@pytest.fixture(autouse=True)
def block_external_http(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("External HTTP is disabled in tests; mock the service")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)

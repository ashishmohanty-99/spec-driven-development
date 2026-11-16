"""pytest configuration for the SpecPilot regression suite (pytest + pytest-playwright)."""
import importlib.util

import pytest

INSTALL = "pytest-playwright is not installed. Run: pip install pytest-playwright && playwright install chromium"


def pytest_configure(config):
    config.addinivalue_line("markers", "requirement(id): the spec requirement this test proves")


if importlib.util.find_spec("pytest_playwright") is None:

    @pytest.fixture
    def page():
        """Stand-in so a missing browser dependency is reported clearly, once per test."""
        from ui_connector import missing

        missing(INSTALL)

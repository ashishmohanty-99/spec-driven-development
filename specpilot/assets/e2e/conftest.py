"""pytest configuration for the SpecPilot regression suite (pytest + pytest-playwright)."""


def pytest_configure(config):
    config.addinivalue_line("markers", "requirement(id): the spec requirement this test proves")

import pytest

print("Loading minimal_conftest.py")


@pytest.fixture
def simple_fixture():
    print("Running simple_fixture")
    return "hello"

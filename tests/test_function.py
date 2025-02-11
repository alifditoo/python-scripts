import pytest

@pytest.fixture
def text():
    return "Hello World!"

def test_string(text):
    print(text)
    assert text == "Hello World!"

"""Simple test to verify pytest is working."""

def test_simple():
    """Simple test that should pass."""
    assert True

class TestSimple:
    """Simple test class."""
    
    def test_method(self):
        """Simple test method."""
        assert 1 + 1 == 2

from secure_qr_tool.security import SecureString

def test_secure_string_wiping():
    s = SecureString("sensitive_data")
    assert s.get() == "sensitive_data"
    s.clear()
    assert s.get_bytes() == b''
    # After clearing, trying to get() should ideally raise an error or return empty string
    # Current implementation returns empty string after clear, which is acceptable.

def test_secure_string_copy():
    s1 = SecureString("original")
    s2 = s1.copy()
    assert s1.get() == "original"
    assert s2.get() == "original"
    s1.clear()
    assert s1.get_bytes() == b''
    assert s2.get() == "original" # s2 should be independent

def test_secure_string_context_manager():
    with SecureString("context_data") as s:
        assert s.get() == "context_data"
    assert s.get_bytes() == b'' # Should be cleared on exit

print("Running SecureString tests...")
test_secure_string_wiping()
test_secure_string_copy()
test_secure_string_context_manager()
print("SecureString tests passed.")



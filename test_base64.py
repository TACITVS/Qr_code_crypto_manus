
import base64
import binascii

def test_malformed_base64():
    malformed_data = "!@#$"
    try:
        base64.b64decode(malformed_data)
        assert False, "Decoding malformed data should have raised an exception"
    except (binascii.Error, ValueError) as e:
        print(f"Successfully caught expected error: {e}")
        # Check if the error message contains expected phrases
        assert "Invalid base64-encoded string" in str(e) or "Incorrect padding" in str(e) or "Non-base64 digit found" in str(e)

print("Running isolated base64 test...")
test_malformed_base64()
print("Isolated base64 test passed.")



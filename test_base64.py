
import base64
import binascii

def test_malformed_base64():
    malformed_data = "!@#$"
    try:
        base64.b64decode(malformed_data, validate=True)
        assert False, "Decoding malformed data should have raised an exception"
    except (binascii.Error, ValueError) as e:
        print(f"Successfully caught expected error: {e}")
        # Check if the error message contains expected phrases
        message = str(e)
        assert (
            "Invalid base64-encoded string" in message
            or "Incorrect padding" in message
            or "Non-base64 digit found" in message
            or "Only base64 data is allowed" in message
        )

print("Running isolated base64 test...")
test_malformed_base64()
print("Isolated base64 test passed.")



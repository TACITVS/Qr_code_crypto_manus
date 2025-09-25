
import json
from src.secure_qr_tool.config import AppConfig
from src.secure_qr_tool.security import CryptoManager, MnemonicManager, SecureString

def test_mnemonic_generation_and_validation():
    config = AppConfig()
    mnemonic_manager = MnemonicManager(config)

    # Test default word count generation
    mnemonic_24_words = mnemonic_manager.generate()
    words = mnemonic_24_words.split()
    assert len(words) == 24
    assert mnemonic_manager.validate(mnemonic_24_words)

    # Test specific word count generation
    mnemonic_12_words = mnemonic_manager.generate(12)
    words = mnemonic_12_words.split()
    assert len(words) == 12
    assert mnemonic_manager.validate(mnemonic_12_words)

    # Test invalid mnemonic
    invalid_mnemonic = "this is not a valid mnemonic phrase"
    assert not mnemonic_manager.validate(invalid_mnemonic)

    # Test checksum
    mnemonic_for_checksum = mnemonic_manager.generate()
    checksum = MnemonicManager.checksum(mnemonic_for_checksum)
    assert len(checksum) == 6
    assert checksum.isupper()

    print("MnemonicManager tests passed.")

def test_crypto_encryption_decryption():
    config = AppConfig()
    crypto_manager = CryptoManager(config)

    password_str = "MySuperSecurePassword123!"
    password = SecureString(password_str)
    original_data_str = "This is some sensitive data to encrypt."
    original_data = SecureString(original_data_str)

    # Test encryption
    encrypted_payload = crypto_manager.encrypt(original_data, password)
    assert "salt" in encrypted_payload
    assert "nonce" in encrypted_payload
    assert "ciphertext" in encrypted_payload
    assert "version" in encrypted_payload

    # Test decryption with correct password
    decrypted_data = crypto_manager.decrypt(encrypted_payload, password)
    assert decrypted_data.get() == original_data_str

    # Test decryption with incorrect password
    wrong_password = SecureString("WrongPassword")
    try:
        crypto_manager.decrypt(encrypted_payload, wrong_password)
        assert False, "Decryption with wrong password should fail"
    except ValueError as e:
        assert "Decryption failed" in str(e)

    # Test with invalid payload (missing fields)
    invalid_payload = {"salt": "abc", "nonce": "def"}
    try:
        crypto_manager.decrypt(invalid_payload, password)
        assert False, "Decryption with invalid payload should fail"
    except ValueError as e:
        assert "Invalid payload, missing fields" in str(e)

    # Test with invalid base64 data (non-base64 characters)
    malformed_payload_chars = {
        "salt": "!@#$",
        "nonce": "abcd",
        "ciphertext": "efgh",
        "version": "1.0",
    }
    try:
        crypto_manager.decrypt(malformed_payload_chars, password)
        assert False, "Decryption with malformed base64 characters should fail"
    except ValueError as e:
        assert "Decryption failed" in str(e) # The security.py decrypt method re-raises as "Decryption failed"

    # Test with valid base64 but incorrect length for nonce/salt/ciphertext
    # The cryptography library raises ValueError for incorrect nonce length
    malformed_payload_length = {
        "salt": "MTIzNDU2Nzg5MDEyMzQ1Ng==", # 16 bytes
        "nonce": "MTIz", # 3 bytes, too short
        "ciphertext": "MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI=",
        "version": "1.0",
    }
    try:
        crypto_manager.decrypt(malformed_payload_length, password)
        assert False, "Decryption with incorrect length base64 should fail"
    except ValueError as e:
        assert "Decryption failed" in str(e) or "Nonce must be between 8 and 128 bytes" in str(e)

    # Ensure SecureString is cleared after use
    original_data.clear()
    password.clear()
    wrong_password.clear()

    print("CryptoManager tests passed.")

print("Running CryptoManager and MnemonicManager tests...")
test_mnemonic_generation_and_validation()
test_crypto_encryption_decryption()
print("All CryptoManager and MnemonicManager tests passed.")



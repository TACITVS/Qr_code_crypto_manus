
import os
import json
from pathlib import Path
from src.secure_qr_tool.config import AppConfig
from src.secure_qr_tool.qr import QRCodeManager

def test_qr_code_manager():
    config = AppConfig()
    qr_manager = QRCodeManager(config)

    # Test is_available
    assert qr_manager.is_available()

    # Test payload_digest
    test_data = "Hello World!"
    digest = qr_manager.payload_digest(test_data)
    assert len(digest) == 64  # SHA-256 is 64 hex characters
    assert isinstance(digest, str)

    # Test save_png and read_from_file
    output_dir = Path("qr_test_output")
    output_dir.mkdir(exist_ok=True)
    qr_path = output_dir / "test_qr.png"

    # Data to be encoded
    data_to_encode = json.dumps({"message": "This is a test QR code payload.", "value": 123})

    # Save QR code with higher scale and border for better readability
    # Temporarily modify config for testing purposes if needed, or pass directly to save_png if API allows
    # For now, assume default config values are used by save_png
    saved_digest = qr_manager.save_png(data_to_encode, str(qr_path))
    assert saved_digest == qr_manager.payload_digest(data_to_encode)
    assert qr_path.exists()

    # Read QR code
    decoded_data = qr_manager.read_from_file(str(qr_path))
    assert decoded_data is not None, f"Failed to decode QR code from {qr_path}. Decoded data: {decoded_data}"
    assert decoded_data == data_to_encode

    # Test to_qpixmap (requires PyQt, so just check if it runs without error if available)
    try:
        pixmap = qr_manager.to_qpixmap(test_data)
        assert pixmap is not None
        from PyQt5.QtGui import QPixmap
        assert isinstance(pixmap, QPixmap)
    except RuntimeError as e:
        print(f"Skipping to_qpixmap test: {e}")

    # Clean up
    os.remove(qr_path)
    os.rmdir(output_dir)

    print("QRCodeManager tests passed.")

print("Running QRCodeManager tests...")
test_qr_code_manager()
print("All QRCodeManager tests passed.")



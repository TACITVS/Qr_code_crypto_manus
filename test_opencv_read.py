
import cv2
import numpy as np
from pathlib import Path

def test_opencv_image_read():
    # Create a dummy image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img_path = Path("dummy_image.png")
    cv2.imwrite(str(img_path), img)

    # Try to read the image
    read_img = cv2.imread(str(img_path))

    assert read_img is not None, "OpenCV failed to read the image"
    assert read_img.shape == (100, 100, 3), "Image shape mismatch"

    img_path.unlink()
    print("OpenCV image read test passed.")

test_opencv_image_read()



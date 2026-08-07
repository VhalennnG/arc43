import sys
import pytest
from src.ocr import recognize_text, recognize_pdf_text_via_ocr

def test_ocr_file_not_found():
    """Verify that recognize_text raises FileNotFoundError for missing images."""
    with pytest.raises(FileNotFoundError):
        recognize_text("nonexistent_image_file_path.png")

def test_pdf_ocr_file_not_found():
    """Verify that recognize_pdf_text_via_ocr raises FileNotFoundError for missing PDFs."""
    with pytest.raises(FileNotFoundError):
        recognize_pdf_text_via_ocr("nonexistent_pdf_file_path.pdf")

def test_vision_framework_bindings():
    """Verify that Apple Vision Framework and Quartz bindings are loadable on macOS."""
    if sys.platform == "darwin":
        try:
            import Vision
            import Quartz
            from Cocoa import NSURL
            from Foundation import NSDictionary
            
            assert hasattr(Vision, "VNRecognizeTextRequest")
            assert hasattr(Vision, "VNImageRequestHandler")
            assert hasattr(Quartz, "CIImage")
            assert hasattr(NSURL, "fileURLWithPath_")
            assert hasattr(NSDictionary, "dictionaryWithDictionary_")
        except ImportError as e:
            pytest.fail(f"Failed to import native macOS frameworks: {e}")
    else:
        pytest.skip("Native Apple Vision testing requires macOS environment.")

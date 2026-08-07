import os
import Quartz
import Vision
from Cocoa import NSURL
from Foundation import NSDictionary

def recognize_text(image_path: str) -> str:
    """
    Extracts text from an image using macOS native Vision Framework via pyobjc.
    Returns the extracted text as a single string (lines joined by newlines).
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # Convert file path to NSURL
    abs_path = os.path.abspath(image_path)
    input_url = NSURL.fileURLWithPath_(abs_path)
    
    # Load image into a CIImage
    input_image = Quartz.CIImage.imageWithContentsOfURL_(input_url)
    if input_image is None:
        raise ValueError(f"Failed to load image from path: {abs_path}")
        
    # Set up request options
    vision_options = NSDictionary.dictionaryWithDictionary_({})
    
    # Create request handler
    vision_handler = Vision.VNImageRequestHandler.alloc().initWithCIImage_options_(
        input_image, 
        vision_options
    )
    
    results = []
    
    # Define completion handler callback
    def completion_handler(request, error):
        if error:
            print(f"Vision OCR Request Callback Error: {error}")
            return
        
        request_results = request.results()
        if request_results:
            for observation in request_results:
                candidates = observation.topCandidates_(1)
                if candidates:
                    results.append(candidates[0].string())
                    
    # Initialize the text recognition request
    text_request = Vision.VNRecognizeTextRequest.alloc().initWithCompletionHandler_(
        completion_handler
    )
    
    # Set recognition level to accurate (0 = accurate, 1 = fast)
    # This aligns with the PRD targeting printed/official documents with high precision.
    try:
        text_request.setRecognitionLevel_(0)
    except AttributeError:
        # Fallback to direct attribute setting if setRecognitionLevel_ is not mapped directly
        text_request.recognitionLevel = 0
    
    # Perform requests
    success, error = vision_handler.performRequests_error_([text_request], None)
    
    if not success:
        raise RuntimeError(f"OCR request execution failed: {error}")
        
    return "\n".join(results)

def recognize_pdf_text_via_ocr(pdf_path: str) -> str:
    """
    Renders each page of a PDF file to a temporary image and extracts text page-by-page.
    """
    import AppKit
    from Quartz import PDFDocument, kPDFDisplayBoxMediaBox
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
    abs_pdf_path = os.path.abspath(pdf_path)
    url = NSURL.fileURLWithPath_(abs_pdf_path)
    pdf_doc = PDFDocument.alloc().initWithURL_(url)
    if not pdf_doc:
        raise ValueError(f"Failed to load PDF document: {pdf_path}")
        
    page_count = pdf_doc.pageCount()
    # Save temporary pages in the temp_uploads folder
    temp_dir = os.path.join(os.path.dirname(os.path.dirname(abs_pdf_path)), "data", "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    
    text_parts = []
    for i in range(page_count):
        page = pdf_doc.pageAtIndex_(i)
        box = kPDFDisplayBoxMediaBox
        bounds = page.boundsForBox_(box)
        width = int(bounds.size.width)
        height = int(bounds.size.height)
        
        if width <= 0 or height <= 0:
            continue
            
        # Initialize an NSImage with the page dimensions
        image = AppKit.NSImage.alloc().initWithSize_((width, height))
        image.lockFocus()
        context = AppKit.NSGraphicsContext.currentContext().graphicsPort()
        page.drawWithBox_toContext_(box, context)
        image.unlockFocus()
        
        # Save NSImage to temporary JPEG
        temp_img_path = os.path.join(temp_dir, f"temp_page_{i}_{os.path.basename(pdf_path)}.jpg")
        tiff_data = image.TIFFRepresentation()
        image_rep = AppKit.NSBitmapImageRep.imageRepWithData_(tiff_data)
        props = AppKit.NSDictionary.dictionaryWithDictionary_({})
        jpeg_data = image_rep.representationUsingType_properties_(3, props) # 3 = NSBitmapImageFileTypeJPEG
        
        if jpeg_data.writeToFile_atomically_(temp_img_path, True):
            try:
                page_text = recognize_text(temp_img_path)
                if page_text.strip():
                    text_parts.append(page_text.strip())
            finally:
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
        else:
            print(f"Warning: Failed to render page {i} of PDF to temporary image.")
            
    return "\n".join(text_parts)


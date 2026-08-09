import os
from typing import List, Tuple
from src.writers.base import DocumentWriter
from src.fields.models import FormField, FieldType

class PDFOverlayWriter(DocumentWriter):
    """
    Writer for static PDF documents.
    Draws text overlays inside bounding boxes using neighboring font properties (A6).
    Auto-shrinks font on overflow and flags fields that cannot fit (#9).
    """

    def map_font_name(self, font_name: str) -> str:
        """
        Maps a system font name to a standard PDF core font (Times, Courier, Helvetica).
        """
        font_name = font_name.lower()
        if "times" in font_name:
            return "times"  # Times-Roman
        elif "courier" in font_name:
            return "cour"   # Courier
        elif "helvetica" in font_name or "arial" in font_name or "sans" in font_name:
            return "helv"   # Helvetica
        else:
            return "helv"   # Fallback

    def detect_font_properties(self, page, bbox: Tuple[float, float, float, float]) -> Tuple[str, float]:
        """
        Finds the neighboring font and size of the text immediately to the left of the bbox.
        Falls back to the median font size of the page.
        """
        import fitz
        spans = []
        page_dict = page.get_text("dict")
        
        # Collect all spans on the page
        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    spans.append(span)
                    
        if not spans:
            return "helv", 10.0
            
        # 1. Look for neighboring label text to the left of our bbox on the same line
        x0_field, y0_field, _, y1_field = bbox
        label_span = None
        min_dist = float("inf")
        
        for span in spans:
            # Check if span is on the same vertical line (approximate) and to the left
            span_rect = span["bbox"] # (x0, y0, x1, y1)
            span_y_center = (span_rect[1] + span_rect[3]) / 2
            field_y_center = (y0_field + y1_field) / 2
            
            if abs(span_y_center - field_y_center) < 8:
                if span_rect[2] <= x0_field + 5:
                    dist = x0_field - span_rect[2]
                    if dist < min_dist:
                        min_dist = dist
                        label_span = span
                        
        if label_span:
            mapped_font = self.map_font_name(label_span["font"])
            # Ensure font size is positive and reasonable
            fontsize = max(6.0, min(16.0, label_span["size"]))
            return mapped_font, fontsize
            
        # 2. Fallback: calculate median font size of the page
        sizes = [s["size"] for s in spans if s["size"] > 0]
        if sizes:
            sorted_sizes = sorted(sizes)
            median_size = sorted_sizes[len(sorted_sizes) // 2]
            return "helv", max(6.0, min(16.0, median_size))
            
        return "helv", 10.0

    def fill(self, source_path: str, fields: List[FormField], output_path: str) -> None:
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"PDF template not found: {source_path}")
            
        import fitz
        doc = fitz.open(source_path)
        
        for field in fields:
            if field.answer is None or not field.page or not field.bbox:
                continue
                
            page_idx = field.page - 1
            if page_idx >= len(doc):
                continue
                
            page = doc[page_idx]
            
            # Detect font properties from neighborhood
            font_name, font_size = self.detect_font_properties(page, field.bbox)
            
            # Make sure bbox is valid
            x0, y0, x1, y1 = field.bbox
            
            # Align bbox to draw text neatly
            # Ensure text box has a minimum height to avoid clipping
            height = y1 - y0
            if height < font_size + 4:
                y1 = y0 + font_size + 4
                
            rect = fitz.Rect(x0, y0, x1, y1)
            
            try:
                # Draw text inside bounding box using insert_textbox (A5/A6)
                # Check return value for overflow (#9)
                rc = page.insert_textbox(
                    rect, 
                    str(field.answer), 
                    fontname=font_name, 
                    fontsize=font_size, 
                    align=0 # left-aligned
                )
                
                # If text overflows (rc < 0), try progressively smaller font sizes
                if rc < 0:
                    for smaller_size in [font_size * 0.85, font_size * 0.7, 6.0]:
                        rc = page.insert_textbox(
                            rect,
                            str(field.answer),
                            fontname=font_name,
                            fontsize=smaller_size,
                            align=0
                        )
                        if rc >= 0:
                            break
                    
                    # If still overflowing at minimum size, flag for manual review
                    if rc < 0:
                        if field.metadata is None:
                            field.metadata = {}
                        field.metadata["overflow_warning"] = True
                        
            except Exception as e:
                print(f"Error overlaying text on PDF page {field.page}: {e}")
                
        doc.save(output_path)
        doc.close()

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def generate_pdf(translated_text: str, output_path: str):
    """
    Generates a PDF file from translated text.
    Handles Tamil font registration if available.
    """
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Font configuration
    # Note: ReportLab default fonts don't support Tamil. 
    # We need a Tamil valid TTF font (e.g., Latha, Nirmala UI, or NotoSansTamil).
    # For now, we will try to load a standard one or fallback to English-compatible font (which will show boxes for Tamil).
    
    # Ideally, the user should provide a font path.
    # I'll check for a common path or assume one is provided in `fonts/` dir if I were thorough.
    # For this prototype, I'll use Helvetica but warn about Tamil rendering.
    
    try:
        # Load Fonts based on likely content (naive approach: load both or check text)
        # For simplicity, we register both if available and use one. 
        # Ideally, we switch font based on language.
        
        tamil_font = "/System/Library/Fonts/Supplemental/Tamil MN.ttc"
        devanagari_font = "/System/Library/Fonts/Supplemental/DevanagariMT.ttc" 
        
        font_name = "Helvetica"
        if os.path.exists(tamil_font):
             pdfmetrics.registerFont(TTFont('Tamil', tamil_font))
        
        if os.path.exists(devanagari_font):
             pdfmetrics.registerFont(TTFont('Hindi', devanagari_font))
             
        # Simple heuristic: Check if text contains Devanagari chars
        if any('\u0900' <= char <= '\u097F' for char in translated_text):
             font_name = 'Hindi' if 'Hindi' in pdfmetrics.getRegisteredFontNames() else "Helvetica"
        elif any('\u0B80' <= char <= '\u0BFF' for char in translated_text):
             font_name = 'Tamil' if 'Tamil' in pdfmetrics.getRegisteredFontNames() else "Helvetica"
             
        c.setFont(font_name, 12)
    except Exception as e:
        print(f"Font loading error: {e}")
        c.setFont("Helvetica", 12)
        
    text_object = c.beginText(inch, height - inch)
    
    # Simple line wrapping logic
    lines = translated_text.split('\n')
    for line in lines:
        # super basic wrapping or just print line
        # ReportLab has better Flowables (Paragraph) for real docs, but this is a prototype.
        text_object.textLine(line)
        
    c.drawText(text_object)
    c.showPage()
    c.save()
    return output_path

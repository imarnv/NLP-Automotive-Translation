from docx import Document
from copy import deepcopy

def translate_docx(input_path, output_path, translate_func, target_lang_code, progress_callback=None):
    """
    Translates a DOCX file while preserving layout.
    Translate_func should accept (list_of_strings, target_lang_code) and return list_of_strings.
    """
    doc = Document(input_path)
    
    # Collect all text to translate
    # We need to map (obj, attribute) -> text so we can replace it later
    # This is complex because we want to batch translate for speed.
    
    text_segments = []
    
    # helper to collect text from a paragraph
    def process_paragraph(para):
        # We process runs to keep formatting? 
        # Actually translating runs individually is bad for context.
        # Translating whole paragraph is better for quality but loses specific run formatting (bold/italic) unless we align.
        # A simple approach for Layout Preservation vs Translation Quality tradeoff:
        # 1. Translate whole paragraph text.
        # 2. Replace the *first* run with translated text and clear others? 
        #    -> formatting of first run applies to whole.
        #    -> Bold/Italic mix is lost.
        # 
        # Advanced: Segment by runs? No, breaks grammar.
        # 
        # Compromise:
        # Collect full paragraph text. Translate. 
        # Clear all runs. Add new run with translated text. 
        # Attempt to copy style from the *majority* or *first* run.
        
        if para.text.strip():
            text_segments.append({"type": "paragraph", "obj": para, "text": para.text})

    # helper to process tables
    def process_table(table):
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    process_paragraph(para)

    # 1. Traverse Document
    for para in doc.paragraphs:
        process_paragraph(para)
        
    for table in doc.tables:
        process_table(table)
        
    # 2. Extract texts
    all_texts = [seg["text"] for seg in text_segments]
    
    # 3. Batch Translate
    # Batch size of 8 for stability + progress
    batch_size = 8
    translated_texts = []
    
    for i in range(0, len(all_texts), batch_size):
        batch = all_texts[i:i+batch_size]
        if not batch: continue
        translated_batch = translate_func(batch, target_lang_code)
        translated_texts.extend(translated_batch)
        
        if progress_callback:
            # Scale progress from 30% to 95%
            progress = 30 + int(((i + len(batch)) / len(all_texts)) * 65)
            progress_callback("Translating...", min(progress, 99))
        
    # 4. Apply back
    if len(translated_texts) != len(text_segments):
        print(f"Warning: Count mismatch! Sent {len(text_segments)}, got {len(translated_texts)}")
        # Fallback or strict error? 
        # We'll just map as much as we can.
        
    for i, seg in enumerate(text_segments):
        if i >= len(translated_texts): break
        
        para = seg["obj"]
        translated_text = translated_texts[i]
        
        # Preservation Strategy:
        # Keep paragraph style.
        # Clear existing runs.
        # Add new run with translated text.
        # Try to preserve font info from the first run of the original paragraph.
        
        if not para.runs:
            para.add_run(translated_text)
            continue
            
        # Capture style of first run
        first_run = para.runs[0]
        is_bold = first_run.bold
        is_italic = first_run.italic
        font_name = first_run.font.name
        font_size = first_run.font.size
        color = first_run.font.color.rgb if first_run.font.color else None
        
        # Clear
        for _ in range(len(para.runs)):
            p = para._p
            p.remove(p.getchildren()[0]) # clear content
            
        # Add new
        new_run = para.add_run(translated_text)
        new_run.bold = is_bold
        new_run.italic = is_italic
        if font_name: new_run.font.name = font_name
        if font_size: new_run.font.size = font_size
        if color: new_run.font.color.rgb = color
        
    # Save
    doc.save(output_path)
    return output_path

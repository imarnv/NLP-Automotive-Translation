from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import shutil
import os
import re
from backend.utils.docx_utils import translate_docx
from backend.pipeline.preprocessing import load_glossary, classify_terms, protect_terms
from backend.pipeline.translation import translate_sentences
from backend.pipeline.postprocessing import restore_placeholders
from backend.utils.pdf_gen import generate_pdf

app = FastAPI(title="Document Translation Backend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global progress state
progress_state = {"status": "idle", "percent": 0}

@app.get("/status")
async def health_check():
    return {"status": "ok", "service": "Backend is running"}

@app.get("/progress")
async def get_progress():
    return progress_state

def update_progress(stage, percent):
    global progress_state
    progress_state["status"] = stage
    progress_state["percent"] = percent

def apply_glossary_post_translation(text: str, glossary: dict) -> str:
    """
    Post-translation glossary enforcement.
    Finds any English glossary terms that survived translation and replaces them
    with the correct target-language term from the glossary.
    """
    # Sort by length (longest first) to avoid partial matches
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    
    result = text
    for term in sorted_terms:
        target_val = glossary[term]
        # Match the English term (case-insensitive, whole word)
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        result = pattern.sub(target_val, result)
    
    return result

@app.post("/translate")
def translate_document(
    file: UploadFile = File(...),
    target_lang: str = Form("Tamil"),
    output_format: str = Form("pdf")
):
    global progress_state
    update_progress("Starting...", 0)
    
    # Save uploaded file temporarily
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = f"{upload_dir}/{file.filename}"
    
    # Determine output extension
    filename_lower = file.filename.lower()
    
    if filename_lower.endswith(".docx"):
        output_filename = f"translated_{file.filename}"
    elif output_format.lower() == "pdf":
        output_filename = f"translated_{os.path.splitext(file.filename)[0]}.pdf"
    else:
        output_filename = f"translated_{file.filename}.txt"
        
    output_path = f"{upload_dir}/{output_filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        update_progress("Loading Glossary...", 10)
        
        # Load Glossary
        full_glossary = load_glossary("english_tamil_hindi_glossary.json")
        update_progress("Classifying Terms...", 15)
        protected_glossary, _ = classify_terms(full_glossary, target_lang)
        
        # Advanced Translation Helper: Protect -> Translate -> Restore
        def translation_helper(sentences, lang_code):
            final_sentences = []
            
            # 1. Protect Terms
            protected_batch = []
            placeholder_maps = []
            
            for s in sentences:
                prot_text, ph_map = protect_terms(s, protected_glossary)
                # Add extra padding spaces around placeholders to prevent model from merging them with adjacent words
                for ph in ph_map:
                    prot_text = prot_text.replace(ph, f" {ph} ")
                protected_batch.append(prot_text)
                placeholder_maps.append(ph_map)
            
            # If NLLB mangles it, we might need a regex fix later. 
            # But this is the requested "fix" for quality - letting the model see the noun as a token.
            
            translated_batch = translate_sentences(protected_batch, target_lang=target_lang)
            
            # 3. Restore
            for i, trans_s in enumerate(translated_batch):
                # If translation failed (empty string), we just return empty
                if not trans_s: 
                    final_sentences.append("")
                    continue
                    
                restored = restore_placeholders(trans_s, placeholder_maps[i], highlight=True)
                final_sentences.append(restored)
                
            return final_sentences

        update_progress("Initializing AI model...", 25)

        if filename_lower.endswith(".docx"):
            translate_docx(file_path, output_path, translation_helper, target_lang, update_progress)
            
        else:
            # Simple Text File
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Segment
            import nltk
            sentences = nltk.sent_tokenize(content)
            
            update_progress(f"Found {len(sentences)} sentences. Starting...", 30)
            
            # Batch translation with progress updates
            batch_size = 8
            translated_sents = []
            for i in range(0, len(sentences), batch_size):
                batch = sentences[i:i+batch_size]
                if not batch: continue
                
                translated_batch = translation_helper(batch, target_lang)
                translated_sents.extend(translated_batch)
                
                # Update progress (30% to 95%)
                progress = 30 + int(((i + len(batch)) / len(sentences)) * 65)
                update_progress(f"Translating batch {i//batch_size + 1}...", min(progress, 99))

            result_text = "\n".join(translated_sents)
            
            if output_filename.endswith(".pdf"):
                generate_pdf(result_text, output_path)
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result_text)
        
        update_progress("Completed", 100)
        
        return {
            "filename": file.filename,
            "status": "Translation Complete",
            "download_url": f"/download/{output_filename}"
        }
    except Exception as e:
        update_progress("Error", 0)
        print(f"Server Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = f"uploads/{filename}"
    if os.path.exists(file_path):
        # Determine media type
        if filename.endswith('.docx'):
            media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif filename.endswith('.pdf'):
            media_type = 'application/pdf'
        else:
            media_type = 'text/plain'
            
        return FileResponse(file_path, media_type=media_type, filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

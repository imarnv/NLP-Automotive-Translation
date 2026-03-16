from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import uvicorn
import shutil
import os
import re
from backend.utils.docx_utils import translate_docx
from backend.utils.xml_utils import translate_xml
from backend.pipeline.preprocessing import load_glossary, classify_terms, protect_terms
from backend.pipeline.translation import translate_sentences
from backend.pipeline.postprocessing import restore_placeholders
from backend.utils.pdf_gen import generate_pdf
from docx2pdf import convert as docx2pdf_convert

app = FastAPI(title="Document Translation Backend")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    """Post-translation glossary enforcement to catch surviving English terms."""
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    result = text
    for term in sorted_terms:
        target_val = glossary[term]
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
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = f"{upload_dir}/{file.filename}"
    filename_lower = file.filename.lower()
    
    if filename_lower.endswith(".docx"):
        docx_output = f"{upload_dir}/translated_{file.filename}"
        if output_format.lower() == "pdf":
            output_filename = f"translated_{os.path.splitext(file.filename)[0]}.pdf"
        else:
            output_filename = f"translated_{file.filename}"
    elif filename_lower.endswith(".xml"):
        docx_output = None
        output_filename = f"translated_{file.filename}"
    else:
        docx_output = None
        output_filename = f"translated_{file.filename}.txt"
        
    output_path = f"{upload_dir}/{output_filename}"
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        update_progress("Loading Glossary...", 10)
        full_glossary = load_glossary("english_tamil_hindi_glossary.json")
        protected_glossary, _ = classify_terms(full_glossary, target_lang)
        
        def translation_helper(paragraphs, lang_code, progress_callback=None):
            import nltk
            is_xml = filename_lower.endswith(".xml")
            batch_size = 64 if is_xml else 30
            
            # Sentence segmentation and indexing to avoid truncation on long sequences
            all_sentences = []
            para_indices = []
            for para in paragraphs:
                sents = nltk.sent_tokenize(para) if para and para.strip() else []
                if not sents and para: sents = [para]
                all_sentences.extend(sents)
                para_indices.append(len(sents))
                
            final_sentences = []
            total_sents = max(1, len(all_sentences))
            
            for i in range(0, len(all_sentences), batch_size):
                batch_sentences = all_sentences[i : i + batch_size]
                
                # Protect terms
                protected_batch = []
                ph_maps = []
                for s in batch_sentences:
                    prot_text, ph_map = protect_terms(s, protected_glossary)
                    protected_batch.append(prot_text)
                    ph_maps.append(ph_map)
                
                # Translate
                translated_batch = translate_sentences(
                    protected_batch, target_lang=target_lang, fast_mode=is_xml
                )
                
                # Restore
                for j, trans_s in enumerate(translated_batch):
                    if not trans_s:
                        final_sentences.append("")
                        continue
                    restored = restore_placeholders(trans_s, ph_maps[j], highlight=False)
                    restored = apply_glossary_post_translation(restored, protected_glossary)
                    final_sentences.append(restored)
                    
                if progress_callback:
                    current_prog = 10 + int((len(final_sentences) / total_sents) * 80)
                    progress_callback(f"Translating {len(final_sentences)}/{total_sents} sentences...", current_prog)
                    
            # Reconstruct original paragraphs
            final_paragraphs = []
            idx = 0
            for count in para_indices:
                if count == 0:
                    final_paragraphs.append("")
                else:
                    sents_in_para = final_sentences[idx : idx + count]
                    final_paragraphs.append(" ".join([str(s) for s in sents_in_para if s]))
                idx += count
                
            return final_paragraphs

        if filename_lower.endswith(".xml"):
            translate_xml(file_path, output_path, translation_helper, target_lang, update_progress)
        elif filename_lower.endswith(".docx"):
            translate_docx(file_path, docx_output, translation_helper, target_lang, update_progress)
            if output_format.lower() == "pdf":
                try:
                    docx2pdf_convert(docx_output, output_path)
                except:
                    output_path = docx_output
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            translated_paragraphs = translation_helper([content], target_lang, update_progress)
            result_text = translated_paragraphs[0]
            if output_filename.endswith(".pdf"):
                generate_pdf(result_text, output_path)
            else:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result_text)
        
        update_progress("Completed", 100)
        return {"filename": file.filename, "status": "Translation Complete", "download_url": f"/download/{output_filename}"}
    except Exception as e:
        update_progress("Error", 0)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = f"uploads/{filename}"
    if os.path.exists(file_path):
        media_type = 'application/xml' if filename.endswith('.xml') else 'application/pdf' if filename.endswith('.pdf') else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if filename.endswith('.docx') else 'text/plain'
        return FileResponse(file_path, media_type=media_type, filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/evaluate")
def evaluate_xml(
    reference: UploadFile = File(...),
    translated: UploadFile = File(...)
):
    import time
    from bs4 import BeautifulSoup
    from backend.pipeline.evaluation import bleu_score, chrf_score, ter_score, semantic_score, semantic_score_batch

    def clean_text(text):
        if not text:
            return ""
        # Remove markers and collapse whitespace
        text = text.replace("@@", "")
        return re.sub(r'\s+', ' ', text).strip()

    def is_trivial(text):
        if not text or not text.strip():
            return True
        if re.fullmatch(r'[\W_]+', text):
            return True
        return False

    try:
        ref_content = reference.file.read()
        trans_content = translated.file.read()

        ref_soup = BeautifulSoup(ref_content, "xml")
        trans_soup = BeautifulSoup(trans_content, "xml")

        def get_xpath(element):
            components = []
            child = element if element.name else element.parent
            for parent in child.parents:
                siblings = parent.find_all(child.name, recursive=False)
                components.append(
                    child.name if len(siblings) == 1 else '%s[%d]' % (
                        child.name,
                        next(i for i, s in enumerate(siblings, 1) if s is child)
                    )
                )
                child = parent
            components.reverse()
            return '/%s' % '/'.join(components)

        def extract_text_nodes(soup):
            nodes = {}
            for tag in soup.find_all(True):
                if tag.string and tag.string.strip():
                    cleaned = clean_text(tag.string)
                    if cleaned and not is_trivial(cleaned):
                        path = get_xpath(tag)
                        nodes[path] = {
                            "tag": tag.name,
                            "clean": cleaned,
                            "path": path
                        }
            return nodes

        ref_nodes_dict = extract_text_nodes(ref_soup)
        trans_nodes_dict = extract_text_nodes(trans_soup)

        ref_nodes = list(ref_nodes_dict.values())
        trans_nodes = list(trans_nodes_dict.values())

        ref_full = " ".join(n["clean"] for n in ref_nodes)
        trans_full = " ".join(n["clean"] for n in trans_nodes)

        bleu_result = bleu_score(trans_full, ref_full)
        chrf_result = chrf_score(trans_full, ref_full)
        ter_result = ter_score(trans_full, ref_full)
        sem_result = semantic_score(trans_full, ref_full)
        
        # Align using exact XPath matches instead of brittle SequenceMatcher
        aligned_pairs = []
        common_paths = set(ref_nodes_dict.keys()).intersection(set(trans_nodes_dict.keys()))
        
        for path in common_paths:
            aligned_pairs.append({
                "ref": ref_nodes_dict[path],
                "trans": trans_nodes_dict[path]
            })
            
        if aligned_pairs:
            all_hyps = [pair["trans"]["clean"] for pair in aligned_pairs]
            all_refs = [pair["ref"]["clean"] for pair in aligned_pairs]
            
            batch_sem_results = semantic_score_batch(all_hyps, all_refs)
            
            segment_scores = []
            for pair_idx, pair in enumerate(aligned_pairs):
                ref_node = pair["ref"]
                trans_node = pair["trans"]
                
                seg_chrf = chrf_score(trans_node["clean"], ref_node["clean"])
                
                segment_scores.append({
                    "index": pair_idx,
                    "ref_preview": ref_node["clean"][:120],
                    "trans_preview": trans_node["clean"][:120],
                    "chrf": round(seg_chrf["chrf"], 2),
                    "semantic": round(batch_sem_results[pair_idx]["semantic_score"], 2),
                    "tag": ref_node["tag"],
                })
        else:
            segment_scores = []

        min_nodes = len(segment_scores)

        sorted_by_score = sorted(segment_scores, key=lambda x: x["semantic"])
        worst_segments = sorted_by_score[:8]
        best_segments = sorted_by_score[-5:][::-1]

        good_count = sum(1 for s in segment_scores if s["semantic"] >= 75)
        fair_count = sum(1 for s in segment_scores if 40 <= s["semantic"] < 75)
        poor_count = sum(1 for s in segment_scores if s["semantic"] < 40)
        avg_chrf = sum(s["chrf"] for s in segment_scores) / max(len(segment_scores), 1)

        avg_sem = sum(s["semantic"] for s in segment_scores) / max(len(segment_scores), 1)

        recommendations = []
        if len(ref_nodes) != len(trans_nodes):
            diff = abs(len(ref_nodes) - len(trans_nodes))
            recommendations.append({"severity": "high", "title": "Node Mismatch", "detail": f"Reference has {len(ref_nodes)} text nodes but translation has {len(trans_nodes)} ({diff} differ)."})
        
        if min_nodes > 0:
            if (poor_count / min_nodes) > 0.3:
                recommendations.append({"severity": "high", "title": "Poor Meaning Matches", "detail": f"{poor_count} out of {min_nodes} nodes ({(poor_count/min_nodes)*100:.0f}%) scored below 40 Semantic."})
            elif (fair_count / min_nodes) > 0.3:
                recommendations.append({"severity": "medium", "title": "Partial Meaning Matches", "detail": f"{fair_count} nodes ({(fair_count/min_nodes)*100:.0f}%) scored between 40-75 Semantic."})
            elif (good_count / min_nodes) > 0.8:
                recommendations.append({"severity": "low", "title": "Good Semantic Alignment", "detail": f"{good_count} nodes ({(good_count/min_nodes)*100:.0f}%) scored above 75 Semantic."})

        english_words = re.findall(r'\b[a-zA-Z]{5,}\b', trans_full)
        if len(set(english_words)) > 10:
            recommendations.append({"severity": "medium", "title": "English Leakage", "detail": f"Found {len(set(english_words))} unique English words: {', '.join(list(set(english_words))[:10])}. Consider glossaries."})

        return {
            "reference_segments": len(ref_nodes),
            "translated_segments": len(trans_nodes),
            "diagnostics": {
                "avg_segment_semantic": round(avg_sem, 2),
                "segment_count_compared": min_nodes,
                "quality_distribution": {
                    "good": good_count,
                    "fair": fair_count,
                    "poor": poor_count,
                    "good_pct": round((good_count/min_nodes)*100, 1) if min_nodes else 0,
                    "fair_pct": round((fair_count/min_nodes)*100, 1) if min_nodes else 0,
                    "poor_pct": round((poor_count/min_nodes)*100, 1) if min_nodes else 0
                },
                "recommendations": recommendations,
                "worst_segments": worst_segments,
                "best_segments": best_segments,
            },
            "overall_scores": {
                "bleu": bleu_result.get("bleu", 0.0),
                "chrf": chrf_result.get("chrf", 0.0),
                "ter": ter_result.get("ter", 0.0),
                "semantic": sem_result.get("semantic_score", 0.0)
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

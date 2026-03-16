import sys
import os

sys.path.append(os.getcwd())
from backend.pipeline.preprocessing import load_glossary, classify_terms, protect_terms
from backend.pipeline.translation import translate_sentences
from backend.pipeline.postprocessing import restore_placeholders
import nltk

print("Downloading NLTK...")
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)

def apply_glossary_post_translation(text: str, glossary: dict) -> str:
    import re
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    result = text
    for term in sorted_terms:
        target_val = glossary[term]
        pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
        result = pattern.sub(target_val, result)
    return result

def main():
    target_lang = "Tamil"
    
    print("Loading Glossary...")
    full_glossary = load_glossary("english_tamil_hindi_glossary.json")
    protected_glossary, _ = classify_terms(full_glossary, target_lang)
    
    long_text = (
        "Auto gear shift is a transaxle developed in conjunction with an auto gear shift actuator unit (1), "
        "a gear shift and select shaft assembly (2) and a conventional manual transaxle (3) and the clutch pedal is eliminated. "
        "Manual transaxle has high mechanical efficiency of power transmission compared with A/T or CVT and, "
        "electronically controlled clutch operation and gear shift are optimized for fuel economy almost equivalent to manual transaxle model."
    )
    
    paragraphs = [long_text]
    
    # Simulate translation_helper logic
    batch_size = 64
    all_sentences = []
    para_indices = []
    for para in paragraphs:
        sents = nltk.sent_tokenize(para) if para and para.strip() else []
        if not sents and para: sents = [para]
        all_sentences.extend(sents)
        para_indices.append(len(sents))
        
    final_sentences = []
    total_sents = max(1, len(all_sentences))
    
    print(f"Segmented into {total_sents} sentences.")
    
    for i in range(0, len(all_sentences), batch_size):
        batch_sentences = all_sentences[i : i + batch_size]
        
        protected_batch = []
        ph_maps = []
        for s in batch_sentences:
            prot_text, ph_map = protect_terms(s, protected_glossary)
            protected_batch.append(prot_text)
            ph_maps.append(ph_map)
        
        print(f"Translating batch...")
        translated_batch = translate_sentences(
            protected_batch, target_lang=target_lang, fast_mode=True
        )
        
        for j, trans_s in enumerate(translated_batch):
            if not trans_s:
                final_sentences.append("")
                continue
            restored = restore_placeholders(trans_s, ph_maps[j], highlight=True)
            restored = apply_glossary_post_translation(restored, protected_glossary)
            final_sentences.append(restored)
            
    final_paragraphs = []
    idx = 0
    for count in para_indices:
        if count == 0:
            final_paragraphs.append("")
        else:
            sents_in_para = final_sentences[idx : idx + count]
            final_paragraphs.append(" ".join([str(s) for s in sents_in_para if s]))
        idx += count
        
    print("\n--- ORIGINAL ---")
    print(long_text)
    print("\n--- TRANSLATED ---")
    print(final_paragraphs[0])
    
if __name__ == "__main__":
    main()

"""
MOBILE-FRIENDLY GURBANI APP - Streamlit Cloud Compatible
=========================================================
Access from phone browser anywhere in the world!
"""

import streamlit as st
import json
import os
import tempfile
import whisper  # Changed from faster-whisper
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import re

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🙏 Gurbani Finder",
    page_icon="🙏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== CUSTOM CSS FOR MOBILE =====
st.markdown("""
<style>
    .stMarkdown {
        font-size: 18px;
    }
    
    .gurmukhi {
        font-size: 24px;
        font-weight: bold;
        color: #1E3A8A;
        line-height: 1.6;
    }
    
    .english {
        font-size: 18px;
        color: #374151;
        margin-top: 8px;
    }
    
    .page-info {
        font-size: 16px;
        color: #6B7280;
        font-weight: 600;
    }
    
    .stars {
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ===== CONFIGURATION =====
GURBANI_DB = "gurbani.json"

@st.cache_resource
def load_database():
    """Load database once and cache it, download if needed"""
    if not os.path.exists(GURBANI_DB):
        st.info("📥 Downloading Gurbani database... (one-time only, ~135 MB)")
        try:
            import urllib.request
            db_url = "https://github.com/Siracha777/gurbani-finder/releases/download/v1.0.0/gurbani.json"
            
            with st.spinner("Downloading database..."):
                urllib.request.urlretrieve(db_url, GURBANI_DB)
            st.success("✅ Database downloaded!")
        except Exception as e:
            st.error(f"❌ Failed to download database: {e}")
            st.stop()
    
    with open(GURBANI_DB, 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_resource
def load_whisper_model():
    """Load Whisper model once and cache it"""
    return whisper.load_model("small")

# ===== HELPER FUNCTIONS =====
def clean_gurmukhi_text(text):
    """Clean Gurmukhi text"""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('੍', '').replace('्', '')
    cleaned = ''.join(char for char in text if '\u0A00' <= char <= '\u0A7F' or char.isspace())
    return cleaned.strip()

def transcribe_audio(audio_file):
    """Transcribe audio to Devanagari"""
    model = load_whisper_model()
    result = model.transcribe(audio_file, language="pa")
    return result["text"].strip()

def convert_to_gurmukhi(devanagari_text):
    """Convert Devanagari to Gurmukhi"""
    gurmukhi = transliterate(devanagari_text, sanscript.DEVANAGARI, sanscript.GURMUKHI)
    return clean_gurmukhi_text(gurmukhi)

def search_gurbani(query_text, limit=10):
    """Search database"""
    data = load_database()
    query_text = clean_gurmukhi_text(query_text)
    query_words = [w for w in query_text.split() if len(w) > 2]
    
    if not query_words:
        return []
    
    results = []
    for record in data:
        gurmukhi = record.get("gurmukhi", "")
        match_score = sum(1 for word in query_words if word in gurmukhi)
        
        if match_score > 0:
            english_trans = ""
            translations_dict = record.get("translations", {})
            
            if "en" in translations_dict:
                en_list = translations_dict["en"]
                if en_list:
                    for trans in en_list:
                        if trans.get("asset") in ["SBMS", "DSSK"]:
                            english_trans = trans["text"]
                            break
                    if not english_trans and len(en_list) > 0:
                        english_trans = en_list[0]["text"]
            
            results.append({
                "gurmukhi": gurmukhi,
                "english": english_trans,
                "page": record.get("page"),
                "line": record.get("line"),
                "match_score": match_score
            })
    
    results.sort(key=lambda x: x['match_score'], reverse=True)
    return results[:limit]

# ===== MAIN APP =====
st.title("🙏 Gurbani Scripture Finder")
st.markdown("**Find any line from Guru Granth Sahib Ji by uploading audio**")

# ===== TABS =====
tab1, tab2 = st.tabs(["📤 Upload Audio", "🔤 Search Text"])

# ===== TAB 1: AUDIO UPLOAD =====
with tab1:
    st.markdown("### Upload Gurbani Audio Recording")
    
    audio_file = st.file_uploader(
        "Choose an audio file (m4a, mp3, wav)",
        type=['m4a', 'mp3', 'wav', 'ogg'],
        help="Record Gurbani on your phone and upload it here"
    )
    
    if audio_file is not None:
        st.audio(audio_file)
        
        if st.button("🔍 Find in Guru Granth Sahib", type="primary", use_container_width=True):
            with st.spinner("Processing audio..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp_file:
                    tmp_file.write(audio_file.read())
                    tmp_path = tmp_file.name
                
                try:
                    with st.status("Transcribing audio...", expanded=True) as status:
                        st.write("🎤 Listening to audio...")
                        devanagari = transcribe_audio(tmp_path)
                        st.write(f"📝 Transcribed: {devanagari[:100]}...")
                        
                        st.write("🔄 Converting to Gurmukhi...")
                        gurmukhi = convert_to_gurmukhi(devanagari)
                        st.write(f"✨ Gurmukhi: {gurmukhi[:100]}...")
                        
                        st.write("🔍 Searching database...")
                        results = search_gurbani(gurmukhi, limit=5)
                        
                        status.update(label="✅ Processing complete!", state="complete")
                    
                    if results:
                        st.success(f"Found {len(results)} match(es)!")
                        
                        for i, result in enumerate(results, 1):
                            stars = "⭐" * min(result['match_score'], 5)
                            
                            with st.container():
                                st.markdown(f"### {i}. {stars}")
                                st.markdown(f'<div class="gurmukhi">{result["gurmukhi"]}</div>', unsafe_allow_html=True)
                                if result['english']:
                                    st.markdown(f'<div class="english">🇬🇧 {result["english"]}</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="page-info">📄 Ang {result["page"]}, Line {result["line"]}</div>', unsafe_allow_html=True)
                                st.divider()
                    else:
                        st.warning("No matches found. Try recording clearer audio.")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

# ===== TAB 2: TEXT SEARCH =====
with tab2:
    st.markdown("### Search Directly with Gurmukhi Text")
    
    search_text = st.text_input(
        "Enter Gurmukhi text:",
        placeholder="ਵਾਹਿਗੁਰੂ",
        help="Type or paste Gurmukhi text to search"
    )
    
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if search_text:
            with st.spinner("Searching..."):
                results = search_gurbani(search_text, limit=5)
                
                if results:
                    st.success(f"Found {len(results)} match(es)!")
                    
                    for i, result in enumerate(results, 1):
                        stars = "⭐" * min(result['match_score'], 5)
                        
                        with st.container():
                            st.markdown(f"### {i}. {stars}")
                            st.markdown(f'<div class="gurmukhi">{result["gurmukhi"]}</div>', unsafe_allow_html=True)
                            if result['english']:
                                st.markdown(f'<div class="english">🇬🇧 {result["english"]}</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="page-info">📄 Ang {result["page"]}, Line {result["line"]}</div>', unsafe_allow_html=True)
                            st.divider()
                else:
                    st.warning("No matches found.")
        else:
            st.warning("Please enter text to search.")

st.markdown("---")
st.markdown("💡 **Tip:** For best results, record in a quiet environment with clear audio.")
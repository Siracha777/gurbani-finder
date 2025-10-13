"""
GURBANI APP - Fixed & Debugged Version
=======================================
Shows what's happening at each step
"""

import streamlit as st
import os
import tempfile
import requests
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import re
import base64

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🙏 Gurbani Finder",
    page_icon="🙏",
    layout="wide"
)

# ===== CUSTOM CSS =====
st.markdown("""
<style>
    .gurmukhi { font-size: 26px; font-weight: bold; color: #1E3A8A; line-height: 1.8; }
    .english { font-size: 19px; color: #374151; margin-top: 8px; }
    .page-info { font-size: 17px; color: #6B7280; font-weight: 600; }
    .debug { background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# ===== AUDIO CONVERSION =====
def convert_audio_for_google(audio_file_path):
    """Convert audio to format Google accepts"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_file_path)
        if audio.channels > 1:
            audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        output_path = tempfile.mktemp(suffix='.wav')
        audio.export(output_path, format='wav')
        return output_path
    except Exception as e:
        st.error(f"Audio conversion error: {e}")
        return None

# ===== GOOGLE SPEECH-TO-TEXT =====
def transcribe_with_google(audio_file_path):
    """Transcribe using Google API"""
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        if not api_key:
            st.error("❌ Google API key not configured")
            return None
        
        # Convert audio
        converted_path = convert_audio_for_google(audio_file_path)
        if not converted_path:
            return None
        
        with open(converted_path, 'rb') as f:
            audio_content = base64.b64encode(f.read()).decode('utf-8')
        
        if os.path.exists(converted_path):
            os.remove(converted_path)
        
        # Try multiple language codes
        language_configs = [
            {"languageCode": "pa-IN", "alternativeLanguageCodes": ["hi-IN"]},
            {"languageCode": "hi-IN", "alternativeLanguageCodes": ["pa-IN"]},
        ]
        
        for config in language_configs:
            url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
            payload = {
                "config": {
                    "encoding": "LINEAR16",
                    "sampleRateHertz": 16000,
                    "enableAutomaticPunctuation": True,
                    **config
                },
                "audio": {"content": audio_content}
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'results' in result and result['results']:
                    transcript = result['results'][0]['alternatives'][0]['transcript']
                    confidence = result['results'][0]['alternatives'][0].get('confidence', 0)
                    return transcript, confidence
        
        return None, 0
    except Exception as e:
        st.error(f"Transcription error: {e}")
        return None, 0

# ===== TEXT PROCESSING =====
def clean_gurmukhi_text(text):
    """Clean Gurmukhi text"""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('੍', '').replace('्', '')
    cleaned = ''.join(char for char in text if '\u0A00' <= char <= '\u0A7F' or char.isspace())
    return cleaned.strip()

def convert_to_gurmukhi(text):
    """Convert Devanagari/Hindi to Gurmukhi"""
    # First try direct conversion
    gurmukhi = transliterate(text, sanscript.DEVANAGARI, sanscript.GURMUKHI)
    return clean_gurmukhi_text(gurmukhi)

# ===== SEARCH =====
def search_sttm_api(query_text, limit=10):
    """Search SikhiToTheMax API"""
    try:
        query_text = clean_gurmukhi_text(query_text)
        words = [w for w in query_text.split() if len(w) > 1]
        
        if not words:
            return []
        
        results = []
        
        # Try different search patterns
        search_patterns = [
            " ".join(words[:6]),
            " ".join(words[:4]),
            " ".join(words[:3]),
            " ".join(words[1:4]) if len(words) > 3 else None,
        ]
        
        for pattern in search_patterns:
            if not pattern:
                continue
                
            url = "https://api.banidb.com/v2/search"
            params = {
                'q': pattern,
                'searchtype': 'first-letters-anywhere',
                'source': 'all',
                'limit': 20
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'verses' in data and data['verses']:
                    for verse in data['verses']:
                        gurmukhi = verse.get('verse', {}).get('gurmukhi', '')
                        
                        # Calculate similarity
                        from difflib import SequenceMatcher
                        similarity = SequenceMatcher(None, query_text.lower(), gurmukhi.lower()).ratio()
                        
                        english = ""
                        translations = verse.get('verse', {}).get('translation', {})
                        if 'en' in translations:
                            english = translations['en'].get('bdb', '')
                        
                        page = verse.get('verse', {}).get('pageNum', '')
                        
                        results.append({
                            'gurmukhi': gurmukhi,
                            'english': english,
                            'page': page,
                            'similarity': similarity
                        })
        
        # Remove duplicates and sort
        seen = set()
        unique = []
        for r in results:
            if r['gurmukhi'] not in seen:
                seen.add(r['gurmukhi'])
                unique.append(r)
        
        unique.sort(key=lambda x: x['similarity'], reverse=True)
        return unique[:limit]
    
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

# ===== MAIN APP =====
st.title("🙏 Gurbani Scripture Finder")
st.markdown("**Debug Mode - See What's Happening**")

# Check API key
if not st.secrets.get("GOOGLE_API_KEY"):
    st.error("⚠️ Google API key not configured in Streamlit secrets")

# ===== TABS =====
tab1, tab2 = st.tabs(["🎤 Upload Audio", "🔤 Text Search"])

# ===== TAB 1: AUDIO =====
with tab1:
    st.markdown("### 🎤 Upload Gurbani Recording")
    
    show_debug = st.checkbox("Show debug info", value=True)
    
    audio_file = st.file_uploader(
        "Choose audio file",
        type=['m4a', 'mp3', 'wav', 'ogg']
    )
    
    if audio_file is not None:
        st.audio(audio_file)
        
        if st.button("🔍 Find Scripture", type="primary", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name
            
            try:
                # STEP 1: Transcribe
                with st.spinner("🎤 Transcribing..."):
                    result = transcribe_with_google(tmp_path)
                    
                    if result:
                        transcript, confidence = result
                    else:
                        transcript, confidence = None, 0
                
                if transcript:
                    st.success(f"✅ Transcribed (confidence: {confidence:.0%})")
                    
                    if show_debug:
                        st.markdown(f'<div class="debug">**Raw transcript:** {transcript}</div>', unsafe_allow_html=True)
                    
                    # STEP 2: Convert
                    with st.spinner("🔄 Converting to Gurmukhi..."):
                        gurmukhi = convert_to_gurmukhi(transcript)
                    
                    st.success("✅ Converted to Gurmukhi")
                    
                    if show_debug:
                        st.markdown(f'<div class="debug">**Gurmukhi:** {gurmukhi}</div>', unsafe_allow_html=True)
                        words = [w for w in gurmukhi.split() if len(w) > 1]
                        st.markdown(f'<div class="debug">**Search words:** {", ".join(words[:6])}</div>', unsafe_allow_html=True)
                    
                    # STEP 3: Search
                    with st.spinner("🔍 Searching..."):
                        results = search_sttm_api(gurmukhi, limit=10)
                    
                    # Display results
                    if results:
                        st.success(f"✅ Found {len(results)} match(es)!")
                        
                        for i, r in enumerate(results, 1):
                            sim_pct = int(r['similarity'] * 100)
                            emoji = "🟢" if sim_pct > 70 else "🟡" if sim_pct > 50 else "🔴"
                            
                            with st.container():
                                st.markdown(f"### {emoji} Result {i} ({sim_pct}% match)")
                                st.markdown(f'<div class="gurmukhi">{r["gurmukhi"]}</div>', unsafe_allow_html=True)
                                if r['english']:
                                    st.markdown(f'<div class="english">{r["english"]}</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="page-info">📄 Ang {r["page"]}</div>', unsafe_allow_html=True)
                                st.divider()
                    else:
                        st.warning("❌ No matches found")
                        st.info("💡 Try: Record 10-15 seconds of clear Gurbani")
                else:
                    st.error("❌ Could not transcribe audio")
                    st.info("💡 Try: Speak louder, reduce background noise, or record longer")
            
            except Exception as e:
                st.error(f"Error: {e}")
                if show_debug:
                    import traceback
                    st.code(traceback.format_exc())
            
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

# ===== TAB 2: TEXT SEARCH =====
with tab2:
    st.markdown("### 🔤 Direct Text Search")
    
    search_text = st.text_input(
        "Enter Gurmukhi or Punjabi text:",
        placeholder="ਵਾਹਿਗੁਰੂ"
    )
    
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if search_text:
            with st.spinner("Searching..."):
                results = search_sttm_api(search_text, limit=10)
                
                if results:
                    st.success(f"Found {len(results)} match(es)!")
                    
                    for i, r in enumerate(results, 1):
                        sim_pct = int(r['similarity'] * 100)
                        
                        with st.container():
                            st.markdown(f"### Result {i} ({sim_pct}% match)")
                            st.markdown(f'<div class="gurmukhi">{r["gurmukhi"]}</div>', unsafe_allow_html=True)
                            if r['english']:
                                st.markdown(f'<div class="english">{r["english"]}</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="page-info">📄 Ang {r["page"]}</div>', unsafe_allow_html=True)
                            st.divider()
                else:
                    st.warning("No matches found")

# ===== FOOTER =====
st.markdown("---")
st.markdown("💡 **Tips for best results:**")
st.markdown("• Record 10-15 seconds of clear Gurbani")
st.markdown("• Speak close to the mic with minimal background noise")
st.markdown("• Try the text search if audio isn't working well")
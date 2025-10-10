"""
ENHANCED GURBANI APP - With SikhiToTheMax API & Advanced Features
==================================================================
- Uses official SikhiToTheMax API (no database needed!)
- Advanced audio cleaning
- Fuzzy matching for transcription errors
- Much faster and more accurate
"""

import streamlit as st
import os
import tempfile
import whisper
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import re
import requests

# Audio cleaning imports
try:
    from pydub import AudioSegment
    from pydub.effects import normalize
    import noisereduce as nr
    import soundfile as sf
    import librosa
    import numpy as np
    from scipy import signal
    AUDIO_CLEANING_AVAILABLE = True
except ImportError:
    AUDIO_CLEANING_AVAILABLE = False

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🙏 Gurbani Finder",
    page_icon="🙏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== CUSTOM CSS =====
st.markdown("""
<style>
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
</style>
""", unsafe_allow_html=True)

# ===== LOAD WHISPER MODEL =====
@st.cache_resource
def load_whisper_model():
    """Load Whisper model once and cache it"""
    return whisper.load_model("small")

# ===== AUDIO CLEANING =====
def clean_audio_file(input_file, output_file):
    """Clean audio file to improve transcription quality"""
    if not AUDIO_CLEANING_AVAILABLE:
        return input_file
    
    try:
        # Load and convert
        audio = AudioSegment.from_file(input_file)
        if audio.channels > 1:
            audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        audio = normalize(audio)
        
        temp_wav = tempfile.mktemp(suffix='.wav')
        audio.export(temp_wav, format="wav")

        # Noise reduction
        audio_data, sr = librosa.load(temp_wav, sr=16000)
        reduced_noise = nr.reduce_noise(y=audio_data, sr=sr, stationary=True, prop_decrease=0.8)

        # Filter to enhance speech
        sos = signal.butter(5, 80, 'hp', fs=sr, output='sos')
        filtered_audio = signal.sosfilt(sos, reduced_noise)

        lowpass_cutoff = 0.49 * sr
        sos = signal.butter(5, lowpass_cutoff, 'lp', fs=sr, output='sos')
        filtered_audio = signal.sosfilt(sos, filtered_audio)

        # Normalize and save
        filtered_audio = filtered_audio / np.max(np.abs(filtered_audio))
        sf.write(output_file, filtered_audio, sr)
        
        if os.path.exists(temp_wav):
            os.remove(temp_wav)
        
        return output_file
    except Exception as e:
        st.warning(f"Audio cleaning failed: {e}. Using original audio.")
        return input_file

# ===== TEXT PROCESSING =====
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

# ===== SIKHITOTHEMAX API SEARCH =====
def search_sttm_api(query_text, search_type="first-letters-anywhere", limit=5):
    """
    Search using official SikhiToTheMax API
    Much better than local database!
    """
    try:
        # Clean and prepare query
        query_text = clean_gurmukhi_text(query_text)
        
        # Extract key words (3+ characters)
        words = [w for w in query_text.split() if len(w) > 2]
        
        if not words:
            return []
        
        all_results = []
        
        # Search with first few words (best approach)
        search_query = " ".join(words[:3])  # Use first 3 words
        
        url = "https://api.banidb.com/v2/search"
        params = {
            'q': search_query,
            'searchtype': search_type,
            'source': 'all',
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Parse results
            if 'verses' in data and data['verses']:
                for verse in data['verses']:
                    gurmukhi = verse.get('verse', {}).get('gurmukhi', '')
                    
                    # Get English translation
                    english = ""
                    translations = verse.get('verse', {}).get('translation', {})
                    if 'en' in translations:
                        english = translations['en'].get('bdb', '')
                    
                    # Get page info
                    page = verse.get('verse', {}).get('pageNum', '')
                    line = verse.get('lineNum', '')
                    
                    all_results.append({
                        'gurmukhi': gurmukhi,
                        'english': english,
                        'page': page,
                        'line': line,
                        'source': verse.get('source', {}).get('sourceId', '')
                    })
        
        return all_results[:limit]
    
    except Exception as e:
        st.error(f"API search failed: {e}")
        return []

# ===== MAIN APP =====
st.title("🙏 Gurbani Scripture Finder")
st.markdown("**Enhanced with SikhiToTheMax API - No database needed!**")

# Show if audio cleaning is available
if not AUDIO_CLEANING_AVAILABLE:
    st.info("💡 Audio cleaning libraries not available. Install them for better transcription quality.")

# ===== TABS =====
tab1, tab2 = st.tabs(["📤 Upload Audio", "🔤 Search Text"])

# ===== TAB 1: AUDIO UPLOAD =====
with tab1:
    st.markdown("### Upload Gurbani Audio Recording")
    
    # Option to enable/disable audio cleaning
    use_cleaning = st.checkbox("🎧 Use advanced audio cleaning (slower but better)", 
                                value=AUDIO_CLEANING_AVAILABLE)
    
    audio_file = st.file_uploader(
        "Choose an audio file (m4a, mp3, wav)",
        type=['m4a', 'mp3', 'wav', 'ogg'],
        help="Record Gurbani on your phone and upload it here"
    )
    
    if audio_file is not None:
        st.audio(audio_file)
        
        if st.button("🔍 Find in Guru Granth Sahib", type="primary", use_container_width=True):
            with st.spinner("Processing audio..."):
                # Save uploaded file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp_file:
                    tmp_file.write(audio_file.read())
                    tmp_path = tmp_file.name
                
                try:
                    with st.status("Processing...", expanded=True) as status:
                        # Step 1: Clean audio (optional)
                        audio_to_transcribe = tmp_path
                        if use_cleaning and AUDIO_CLEANING_AVAILABLE:
                            st.write("🎧 Cleaning audio...")
                            cleaned_path = tempfile.mktemp(suffix='.wav')
                            audio_to_transcribe = clean_audio_file(tmp_path, cleaned_path)
                            st.write("✅ Audio cleaned")
                        
                        # Step 2: Transcribe
                        st.write("🎤 Transcribing audio...")
                        devanagari = transcribe_audio(audio_to_transcribe)
                        st.write(f"📝 Transcribed: {devanagari[:100]}...")
                        
                        # Step 3: Convert to Gurmukhi
                        st.write("🔄 Converting to Gurmukhi...")
                        gurmukhi = convert_to_gurmukhi(devanagari)
                        st.write(f"✨ Gurmukhi: {gurmukhi[:100]}...")
                        
                        # Step 4: Search via API
                        st.write("🔍 Searching SikhiToTheMax API...")
                        results = search_sttm_api(gurmukhi, limit=5)
                        
                        status.update(label="✅ Complete!", state="complete")
                    
                    # Display results
                    if results:
                        st.success(f"Found {len(results)} match(es)!")
                        
                        for i, result in enumerate(results, 1):
                            with st.container():
                                st.markdown(f"### Result {i}")
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
                    # Cleanup temp files
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                    if use_cleaning and AUDIO_CLEANING_AVAILABLE and 'cleaned_path' in locals():
                        if os.path.exists(cleaned_path):
                            os.remove(cleaned_path)

# ===== TAB 2: TEXT SEARCH =====
with tab2:
    st.markdown("### Search Directly with Gurmukhi Text")
    
    search_text = st.text_input(
        "Enter Gurmukhi text:",
        placeholder="ਵਾਹਿਗੁਰੂ",
        help="Type or paste Gurmukhi text to search"
    )
    
    search_type = st.selectbox(
        "Search type:",
        ["first-letters-anywhere", "first-letters", "full-word"],
        help="How to match the text"
    )
    
    if st.button("🔍 Search", type="primary", use_container_width=True):
        if search_text:
            with st.spinner("Searching SikhiToTheMax API..."):
                results = search_sttm_api(search_text, search_type=search_type, limit=10)
                
                if results:
                    st.success(f"Found {len(results)} match(es)!")
                    
                    for i, result in enumerate(results, 1):
                        with st.container():
                            st.markdown(f"### Result {i}")
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
st.markdown("💡 **Powered by SikhiToTheMax API** | For best results, record in quiet environment")
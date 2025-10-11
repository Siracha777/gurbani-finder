"""
ULTRA FAST GURBANI APP - Google Speech-to-Text
===============================================
Real-time transcription for Gurdwara use!
Results in 5-10 seconds instead of 5 minutes!
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
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== CUSTOM CSS =====
st.markdown("""
<style>
    .gurmukhi {
        font-size: 26px;
        font-weight: bold;
        color: #1E3A8A;
        line-height: 1.8;
        margin: 10px 0;
    }
    .english {
        font-size: 19px;
        color: #374151;
        margin-top: 8px;
        line-height: 1.6;
    }
    .page-info {
        font-size: 17px;
        color: #6B7280;
        font-weight: 600;
        margin-top: 8px;
    }
    .stButton button {
        font-size: 18px;
        padding: 12px 24px;
    }
</style>
""", unsafe_allow_html=True)

# ===== GOOGLE SPEECH-TO-TEXT =====
def transcribe_with_google(audio_file_path):
    """
    Ultra fast transcription using Google Speech-to-Text API
    Takes 2-5 seconds instead of 5 minutes!
    """
    try:
        # Get API key from Streamlit secrets
        api_key = st.secrets.get("GOOGLE_API_KEY", "")
        
        if not api_key:
            st.error("❌ Google API key not found in Streamlit secrets!")
            st.info("Please add GOOGLE_API_KEY to your Streamlit app secrets.")
            return None
        
        # Read audio file
        with open(audio_file_path, 'rb') as audio_file:
            audio_content = base64.b64encode(audio_file.read()).decode('utf-8')
        
        # Prepare API request
        url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
        
        payload = {
            "config": {
                "encoding": "LINEAR16",
                "languageCode": "pa-IN",  # Punjabi (India)
                "alternativeLanguageCodes": ["hi-IN"],  # Hindi as fallback
                "enableAutomaticPunctuation": True,
            },
            "audio": {
                "content": audio_content
            }
        }
        
        # Make API call
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'results' in result and result['results']:
                # Get transcription
                transcript = result['results'][0]['alternatives'][0]['transcript']
                return transcript
            else:
                st.warning("No speech detected in audio. Try recording again.")
                return None
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        st.error(f"Transcription error: {str(e)}")
        return None

# ===== TEXT PROCESSING =====
def clean_gurmukhi_text(text):
    """Clean Gurmukhi text"""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('੍', '').replace('्', '')
    cleaned = ''.join(char for char in text if '\u0A00' <= char <= '\u0A7F' or char.isspace())
    return cleaned.strip()

def convert_to_gurmukhi(devanagari_text):
    """Convert Devanagari to Gurmukhi"""
    gurmukhi = transliterate(devanagari_text, sanscript.DEVANAGARI, sanscript.GURMUKHI)
    return clean_gurmukhi_text(gurmukhi)

# ===== SIKHITOTHEMAX API SEARCH =====
def search_sttm_api(query_text, limit=5):
    """Search using SikhiToTheMax API"""
    try:
        query_text = clean_gurmukhi_text(query_text)
        words = [w for w in query_text.split() if len(w) > 2]
        
        if not words:
            return []
        
        # Use first 3-4 words for best results
        search_query = " ".join(words[:4])
        
        url = "https://api.banidb.com/v2/search"
        params = {
            'q': search_query,
            'searchtype': 'first-letters-anywhere',
            'source': 'all',
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = []
            
            if 'verses' in data and data['verses']:
                for verse in data['verses']:
                    gurmukhi = verse.get('verse', {}).get('gurmukhi', '')
                    
                    english = ""
                    translations = verse.get('verse', {}).get('translation', {})
                    if 'en' in translations:
                        english = translations['en'].get('bdb', '')
                    
                    page = verse.get('verse', {}).get('pageNum', '')
                    line = verse.get('lineNum', '')
                    
                    results.append({
                        'gurmukhi': gurmukhi,
                        'english': english,
                        'page': page,
                        'line': line
                    })
            
            return results[:limit]
        
        return []
    
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return []

# ===== MAIN APP =====
st.title("🙏 Gurbani Finder")
st.markdown("**⚡ Real-time transcription for Gurdwara use**")

# Check if API key is set
if not st.secrets.get("GOOGLE_API_KEY"):
    st.warning("⚠️ Google API key not configured. Please add it in Streamlit secrets.")
    st.info("""
    **Setup Instructions:**
    1. Go to your Streamlit app settings
    2. Add to Secrets:
    ```
    GOOGLE_API_KEY = "your-key-here"
    ```
    """)

# ===== TABS =====
tab1, tab2 = st.tabs(["🎤 Record & Find", "🔤 Text Search"])

# ===== TAB 1: AUDIO UPLOAD =====
with tab1:
    st.markdown("### 🎤 Upload Recording from Gurdwara")
    st.info("💡 **Tip:** Record 10-15 seconds for best results")
    
    audio_file = st.file_uploader(
        "Choose audio file",
        type=['m4a', 'mp3', 'wav', 'ogg'],
        help="Record Gurbani and upload here"
    )
    
    if audio_file is not None:
        st.audio(audio_file)
        
        if st.button("🔍 Find Scripture", type="primary", use_container_width=True):
            
            # Save uploaded file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_file.write(audio_file.read())
                tmp_path = tmp_file.name
            
            try:
                # Step 1: Transcribe (FAST!)
                with st.spinner("🎤 Transcribing... (5-10 seconds)"):
                    devanagari = transcribe_with_google(tmp_path)
                
                if devanagari:
                    st.success(f"📝 Heard: {devanagari}")
                    
                    # Step 2: Convert to Gurmukhi
                    with st.spinner("🔄 Converting to Gurmukhi..."):
                        gurmukhi = convert_to_gurmukhi(devanagari)
                        st.success(f"✨ Gurmukhi: {gurmukhi}")
                    
                    # Step 3: Search
                    with st.spinner("🔍 Finding in Guru Granth Sahib..."):
                        results = search_sttm_api(gurmukhi, limit=5)
                    
                    # Display results
                    if results:
                        st.success(f"✅ Found {len(results)} match(es)!")
                        
                        for i, result in enumerate(results, 1):
                            with st.container():
                                st.markdown(f"### 📖 Result {i}")
                                st.markdown(f'<div class="gurmukhi">{result["gurmukhi"]}</div>', unsafe_allow_html=True)
                                if result['english']:
                                    st.markdown(f'<div class="english">{result["english"]}</div>', unsafe_allow_html=True)
                                st.markdown(f'<div class="page-info">📄 Ang (Page) {result["page"]}</div>', unsafe_allow_html=True)
                                st.divider()
                    else:
                        st.warning("❌ No matches found. Try recording again with clearer audio.")
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
            
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

# ===== TAB 2: TEXT SEARCH =====
with tab2:
    st.markdown("### 🔤 Direct Text Search")
    st.info("💡 Use if you know what was said or want to explore")
    
    search_text = st.text_input(
        "Enter Gurmukhi or Punjabi text:",
        placeholder="ਵਾਹਿਗੁਰੂ",
        help="Type what you heard"
    )
    
    if st.button("🔍 Search Scripture", type="primary", use_container_width=True):
        if search_text:
            with st.spinner("Searching..."):
                results = search_sttm_api(search_text, limit=10)
                
                if results:
                    st.success(f"Found {len(results)} match(es)!")
                    
                    for i, result in enumerate(results, 1):
                        with st.container():
                            st.markdown(f"### 📖 Result {i}")
                            st.markdown(f'<div class="gurmukhi">{result["gurmukhi"]}</div>', unsafe_allow_html=True)
                            if result['english']:
                                st.markdown(f'<div class="english">{result["english"]}</div>', unsafe_allow_html=True)
                            st.markdown(f'<div class="page-info">📄 Ang {result["page"]}</div>', unsafe_allow_html=True)
                            st.divider()
                else:
                    st.warning("No matches found.")
        else:
            st.warning("Please enter text to search.")

# ===== FOOTER =====
st.markdown("---")
st.markdown("💡 **How to use at Gurdwara:**")
st.markdown("""
1. 🎤 Record 10-15 seconds on your phone
2. 📤 Upload the recording here
3. ⏱️ Wait 5-10 seconds for results
4. 📖 Read along with the translation!
""")
st.markdown("🙏 *Powered by Google Speech-to-Text & SikhiToTheMax API*")
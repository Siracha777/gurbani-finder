"""
GURBANI SCRIPTURE FINDER - Text Search Only
============================================
Paste Gurmukhi text → Get instant results with translations
"""

import streamlit as st
import requests
import re
from difflib import SequenceMatcher

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🙏 Gurbani Finder",
    page_icon="🙏",
    layout="centered"
)

# ===== CUSTOM CSS =====
st.markdown("""
<style>
    .gurmukhi {
        font-size: 28px;
        font-weight: bold;
        color: #0F172A;
        background: #F0F9FF;
        padding: 15px;
        border-radius: 8px;
        line-height: 1.8;
        margin: 15px 0;
        border-left: 4px solid #1E3A8A;
    }
    .english {
        font-size: 20px;
        color: #1F2937;
        background: #F3F4F6;
        padding: 12px;
        border-radius: 6px;
        margin-top: 10px;
        line-height: 1.6;
    }
    .page-info {
        font-size: 18px;
        color: #374151;
        background: #E5E7EB;
        padding: 10px;
        border-radius: 6px;
        font-weight: 600;
        margin-top: 10px;
    }
    .stButton button {
        font-size: 18px;
        padding: 15px;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ===== HELPER FUNCTIONS =====
def clean_gurmukhi_text(text):
    """Clean Gurmukhi text"""
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('੍', '').replace('्', '')
    cleaned = ''.join(char for char in text if '\u0A00' <= char <= '\u0A7F' or char.isspace())
    return cleaned.strip()

def search_gurbani(query_text, limit=15):
    """Search SikhiToTheMax API for Gurmukhi text"""
    try:
        query_text = clean_gurmukhi_text(query_text)
        words = [w for w in query_text.split() if len(w) > 1]
        
        if not words:
            return []
        
        results = []
        
        # Try different word combinations
        search_patterns = [
            " ".join(words[:6]),
            " ".join(words[:4]),
            " ".join(words[:3]),
            " ".join(words[1:4]) if len(words) > 3 else None,
            " ".join(words[-3:]) if len(words) > 3 else None,
        ]
        
        for pattern in search_patterns:
            if not pattern:
                continue
            
            url = "https://api.banidb.com/v2/search"
            params = {
                'q': pattern,
                'searchtype': 'first-letters-anywhere',
                'source': 'all',
                'limit': 30
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'verses' in data and data['verses']:
                    for verse in data['verses']:
                        gurmukhi = verse.get('verse', {}).get('gurmukhi', '')
                        
                        # Calculate similarity
                        similarity = SequenceMatcher(None, query_text.lower(), gurmukhi.lower()).ratio()
                        
                        # Get English translation
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
        
        # Remove duplicates and sort by similarity
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
st.markdown("**Listen to Gurbani → Get Gurmukhi Text → Search Scripture**")
st.markdown("---")

# ===== TABS =====
tab1, tab2, tab3 = st.tabs(["🎤 Audio to Gurmukhi", "🔍 Text Search", "⚡ Fast Local Search"])

# ===== TAB 1: AUDIO TO GURMUKHI =====
with tab1:
    st.markdown("### Step 1: Convert Audio to Gurmukhi Text")
    st.markdown("Record Gurbani on your phone and upload here to get the Gurmukhi text")
    
    audio_file = st.file_uploader(
        "Choose audio file",
        type=['m4a', 'mp3', 'wav', 'ogg'],
        label_visibility="collapsed"
    )
    
    if audio_file is not None:
        st.audio(audio_file)
        
        if st.button("🎤 Convert to Gurmukhi Text", type="primary", use_container_width=True):
            import tempfile
            import os
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate
            import base64
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name
            
            try:
                # Skip pydub conversion - send directly to Google
                with open(tmp_path, 'rb') as f:
                    audio_content = base64.b64encode(f.read()).decode('utf-8')
                
                # Transcribe with Google
                api_key = st.secrets.get("GOOGLE_API_KEY", "")
                if not api_key:
                    st.error("Google API key not configured in Streamlit secrets")
                else:
                    with st.spinner("Transcribing audio..."):
                        url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"
                        
                        # Try different encodings for different file types
                        configs = [
                            {"encoding": "OGG_OPUS"},
                            {"encoding": "MP3"},
                            {"encoding": "FLAC"},
                        ]
                        
                        transcript = None
                        confidence = 0
                        
                        for config in configs:
                            payload = {
                                "config": {
                                    **config,
                                    "languageCode": "pa-IN",
                                    "alternativeLanguageCodes": ["hi-IN"],
                                    "enableAutomaticPunctuation": True,
                                },
                                "audio": {"content": audio_content}
                            }
                            
                            response = requests.post(url, json=payload, timeout=30)
                            
                            if response.status_code == 200:
                                result = response.json()
                                if 'results' in result and result['results']:
                                    transcript = result['results'][0]['alternatives'][0]['transcript']
                                    confidence = result['results'][0]['alternatives'][0].get('confidence', 0)
                                    break
                        
                        if transcript:
                            st.success(f"✅ Transcribed (confidence: {confidence:.0%})")
                            
                            # Convert to Gurmukhi
                            with st.spinner("Converting to Gurmukhi..."):
                                gurmukhi = transliterate(transcript, sanscript.DEVANAGARI, sanscript.GURMUKHI)
                                gurmukhi = clean_gurmukhi_text(gurmukhi)
                            
                            st.success("✅ Converted to Gurmukhi")
                            
                            # Display result
                            st.markdown("### Your Gurmukhi Text:")
                            st.markdown(f'<div class="gurmukhi">{gurmukhi}</div>', unsafe_allow_html=True)
                            
                            # Copy button
                            st.code(gurmukhi, language="text")
                            st.markdown("☝️ **Copy the text above**")
                            st.markdown("Then go to the **'Text Search'** tab and paste it to find matches!")
                        else:
                            st.warning("No speech detected in audio. Try recording again with clearer audio.")
                
            except Exception as e:
                st.error(f"Error: {e}")
            
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

# ===== TAB 2: SEARCH SCRIPTURE =====
with tab2:
    st.markdown("### Step 2: Search Scripture")
    st.markdown("Paste the Gurmukhi text from Step 1 (or any Gurmukhi text) to find matches")
    
    search_text = st.text_area(
        "Paste Gurmukhi text here:",
        placeholder="ਗਹਿ ਭੁਜਾ ਲੀਨੇ. ਦਇਆ ਕੀਨੇ; ਆਪਨੇ ਕਰਿ ਮਾਨਿਆ ॥",
        height=100,
        label_visibility="collapsed"
    )
    
    if st.button("🔍 Search Scripture", type="primary", use_container_width=True):
        if search_text.strip():
            with st.spinner("Searching..."):
                results = search_gurbani(search_text, limit=15)
            
            st.markdown("---")
            
            if results:
                st.success(f"✅ Found {len(results)} match(es)!")
                st.markdown("")
                
                for i, result in enumerate(results, 1):
                    sim_pct = int(result['similarity'] * 100)
                    
                    if sim_pct >= 85:
                        emoji = "🟢"
                        label = "Exact Match"
                    elif sim_pct >= 70:
                        emoji = "🟡"
                        label = "Good Match"
                    elif sim_pct >= 50:
                        emoji = "🟠"
                        label = "Possible Match"
                    else:
                        emoji = "🔴"
                        label = "Distant Match"
                    
                    with st.container():
                        st.markdown(f"### {emoji} Result {i} - {label} ({sim_pct}%)")
                        st.markdown(f'<div class="gurmukhi">{result["gurmukhi"]}</div>', unsafe_allow_html=True)
                        
                        if result['english']:
                            st.markdown(f'<div class="english">🇬🇧 {result["english"]}</div>', unsafe_allow_html=True)
                        
                        st.markdown(f'<div class="page-info">📄 Ang (Page) {result["page"]}</div>', unsafe_allow_html=True)
                        st.divider()
            else:
                st.warning("No matches found")
        else:
            st.warning("Please paste Gurmukhi text to search")

# ===== FOOTER =====
st.markdown("---")
st.markdown("### 📱 Best Way to Use This App:")
st.markdown("""
**At the Gurdwara:**
1. Listen to Gurbani being recited
2. Type what you hear using a Gurmukhi keyboard
3. Paste here to find the full verse
4. Read the English translation to understand

**Gurmukhi Keyboard Apps:**
- Android: "Punjabi Keyboard" or "Google Gboard with Punjabi"
- iPhone: "Punjabi Keyboard Pro"
- Online: google.com/inputtools (search for Punjabi)
""")

st.markdown("---")
st.markdown("🙏 *Powered by SikhiToTheMax Database*")
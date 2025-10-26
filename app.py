"""
SMART GURBANI IDENTIFIER
========================
Practical approach: Audio → Suggestions → Pick One → Full Shabad
"""

import streamlit as st
import requests
import re
from difflib import SequenceMatcher
import time

# ===== PAGE CONFIG =====
st.set_page_config(
    page_title="🙏 Gurbani Identifier",
    page_icon="🙏",
    layout="centered"
)

# ===== CUSTOM CSS =====
st.markdown("""
<style>
    .gurmukhi {
        font-size: 24px;
        font-weight: bold;
        color: #0F172A;
        background: #F0F9FF;
        padding: 12px;
        border-radius: 6px;
        line-height: 1.8;
        margin: 10px 0;
        border-left: 4px solid #1E3A8A;
    }
    .english {
        font-size: 18px;
        color: #1F2937;
        background: #F3F4F6;
        padding: 10px;
        border-radius: 5px;
        margin: 8px 0;
        line-height: 1.6;
    }
    .page-info {
        font-size: 16px;
        color: #374151;
        background: #E5E7EB;
        padding: 8px;
        border-radius: 5px;
        font-weight: 600;
        margin: 8px 0;
    }
    .shabad-card {
        background: #F9FAFB;
        border: 2px solid #E5E7EB;
        border-radius: 8px;
        padding: 15px;
        margin: 15px 0;
        cursor: pointer;
    }
    .shabad-card:hover {
        border-color: #3B82F6;
        background: #EFF6FF;
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

def search_shabads_fuzzy(query_text, limit=10):
    """Search for shabads with fuzzy matching - return multiple suggestions"""
    try:
        query_text = clean_gurmukhi_text(query_text)
        words = [w for w in query_text.split() if len(w) > 1]
        
        if not words:
            return []
        
        results = []
        seen_shabads = {}
        
        # Search with different word combinations
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
                'limit': 30
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'verses' in data and data['verses']:
                    for verse in data['verses']:
                        shabad_id = verse.get('verse', {}).get('shabadId')
                        
                        if shabad_id and shabad_id not in seen_shabads:
                            gurmukhi = verse.get('verse', {}).get('gurmukhi', '')
                            
                            # Calculate similarity
                            similarity = SequenceMatcher(None, query_text.lower(), gurmukhi.lower()).ratio()
                            
                            english = ""
                            translations = verse.get('verse', {}).get('translation', {})
                            if 'en' in translations:
                                english = translations['en'].get('bdb', '')
                            
                            page = verse.get('verse', {}).get('pageNum', '')
                            
                            seen_shabads[shabad_id] = {
                                'shabad_id': shabad_id,
                                'first_line': gurmukhi,
                                'english': english,
                                'page': page,
                                'similarity': similarity
                            }
        
        # Sort by similarity and return top matches
        results = list(seen_shabads.values())
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]
    
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def get_full_shabad(shabad_id):
    """Get complete shabad by ID"""
    try:
        url = f"https://api.banidb.com/v2/shabads/{shabad_id}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            verses = []
            
            if 'verses' in data:
                for verse in data['verses']:
                    gurmukhi = verse.get('verse', {}).get('gurmukhi', '')
                    
                    english = ""
                    translations = verse.get('verse', {}).get('translation', {})
                    if 'en' in translations:
                        english = translations['en'].get('bdb', '')
                    
                    verses.append({
                        'gurmukhi': gurmukhi,
                        'english': english
                    })
            
            return verses
        return []
    except Exception as e:
        st.error(f"Error loading shabad: {e}")
        return []

# ===== MAIN APP =====
st.title("🙏 Smart Gurbani Identifier")
st.markdown("**Find any Gurbani shabad in seconds**")
st.markdown("---")

# ===== TABS =====
tab1, tab2, tab3 = st.tabs(["🎤 Identify Shabad", "📚 Popular Shabads", "🔍 Text Search"])

# ===== TAB 1: IDENTIFY SHABAD =====
with tab1:
    st.markdown("### 🎤 Identify What's Playing")
    st.info("💡 **How it works:** Upload audio → Get 10 suggestions → Pick the right one → See full shabad!")
    
    audio_file = st.file_uploader(
        "Record 10-15 seconds of Gurbani",
        type=['m4a', 'mp3', 'wav', 'ogg'],
        key="identify_audio"
    )
    
    if audio_file:
        st.audio(audio_file)
        
        if st.button("🔍 Find This Shabad", type="primary", use_container_width=True):
            import tempfile
            import os
            from indic_transliteration import sanscript
            from indic_transliteration.sanscript import transliterate
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp:
                tmp.write(audio_file.read())
                tmp_path = tmp.name
            
            try:
                assembly_key = st.secrets.get("ASSEMBLYAI_API_KEY", "")
                
                if not assembly_key:
                    st.warning("AssemblyAI not configured. Using text search instead.")
                    st.info("💡 Tip: Type what you hear below:")
                else:
                    headers = {'authorization': assembly_key}
                    
                    with st.spinner("Listening to audio..."):
                        # Upload
                        with open(tmp_path, 'rb') as f:
                            upload_response = requests.post(
                                'https://api.assemblyai.com/v2/upload',
                                headers=headers,
                                files={'file': f}
                            )
                        
                        if upload_response.status_code == 200:
                            audio_url = upload_response.json()['upload_url']
                            
                            # Transcribe
                            transcript_response = requests.post(
                                'https://api.assemblyai.com/v2/transcript',
                                json={'audio_url': audio_url, 'language_code': 'hi'},
                                headers=headers
                            )
                            
                            transcript_id = transcript_response.json()['id']
                            polling_endpoint = f'https://api.assemblyai.com/v2/transcript/{transcript_id}'
                            
                            with st.spinner("Finding matching shabads (30 sec)..."):
                                while True:
                                    result = requests.get(polling_endpoint, headers=headers)
                                    status = result.json()['status']
                                    
                                    if status == 'completed':
                                        transcript = result.json()['text']
                                        gurmukhi = transliterate(transcript, sanscript.DEVANAGARI, sanscript.GURMUKHI)
                                        gurmukhi = clean_gurmukhi_text(gurmukhi)
                                        
                                        st.success(f"✅ Heard: {gurmukhi[:100]}...")
                                        
                                        # Search for matches
                                        suggestions = search_shabads_fuzzy(gurmukhi, limit=10)
                                        
                                        if suggestions:
                                            st.markdown("### 📖 Is it one of these shabads?")
                                            st.markdown("Click the shabad you were listening to:")
                                            
                                            for i, sug in enumerate(suggestions, 1):
                                                match_pct = int(sug['similarity'] * 100)
                                                
                                                if st.button(
                                                    f"**{i}.** {sug['first_line'][:80]}... ({match_pct}% match)",
                                                    key=f"sug_{sug['shabad_id']}",
                                                    use_container_width=True
                                                ):
                                                    st.session_state.selected_shabad = sug['shabad_id']
                                                    st.session_state.selected_page = sug['page']
                                                    st.rerun()
                                        else:
                                            st.warning("No matches found. Try text search!")
                                        break
                                    
                                    elif status == 'error':
                                        st.error("Transcription failed")
                                        break
                                    
                                    time.sleep(2)
            
            except Exception as e:
                st.error(f"Error: {e}")
            
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
    
    # Show full shabad if selected
    if 'selected_shabad' in st.session_state:
        st.markdown("---")
        st.markdown("### ✨ Full Shabad")
        
        verses = get_full_shabad(st.session_state.selected_shabad)
        
        if verses:
            st.success(f"📄 Ang (Page) {st.session_state.selected_page}")
            
            for verse in verses:
                st.markdown(f'<div class="gurmukhi">{verse["gurmukhi"]}</div>', unsafe_allow_html=True)
                if verse['english']:
                    st.markdown(f'<div class="english">{verse["english"]}</div>', unsafe_allow_html=True)
                st.markdown("")

# ===== TAB 2: POPULAR SHABADS =====
with tab2:
    st.markdown("### 📚 Most Common Gurdwara Shabads")
    st.info("💡 Browse and click to see full text with translations")
    
    popular_searches = [
        "ਧਨ ਧਨ ਰਾਮ ਦਾਸ ਗੁਰ",
        "ਮੇਰੇ ਮਨ ਲੋਚੈ ਗੁਰ ਦਰਸਨ ਤਾਈ",
        "ਵਾਹਿਗੁਰੂ ਵਾਹਿਗੁਰੂ",
        "ਤੂ ਠਾਕੁਰੁ ਤੁਮ ਪਹਿ ਅਰਦਾਸਿ",
        "ਜਪੁ ਜੀ ਸਾਹਿਬ",
    ]
    
    for search in popular_searches:
        if st.button(search, use_container_width=True, key=f"pop_{search}"):
            st.session_state.text_search = search

# ===== TAB 3: TEXT SEARCH =====
with tab3:
    st.markdown("### 🔍 Search by Text")
    
    search_text = st.text_area(
        "Paste or type Gurmukhi text:",
        value=st.session_state.get('text_search', ''),
        placeholder="ਵਾਹਿਗੁਰੂ",
        height=80
    )
    
    if st.button("Search", type="primary", use_container_width=True):
        if search_text:
            results = search_shabads_fuzzy(search_text, limit=15)
            
            if results:
                st.success(f"Found {len(results)} match(es)!")
                
                for i, r in enumerate(results, 1):
                    sim_pct = int(r['similarity'] * 100)
                    
                    with st.container():
                        st.markdown(f"### Result {i} ({sim_pct}% match)")
                        st.markdown(f'<div class="gurmukhi">{r["first_line"]}</div>', unsafe_allow_html=True)
                        if r['english']:
                            st.markdown(f'<div class="english">{r["english"]}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="page-info">📄 Ang {r["page"]}</div>', unsafe_allow_html=True)
                        st.divider()

st.markdown("---")
st.markdown("💡 **Best Results:** Record 10-15 seconds in a quiet environment")
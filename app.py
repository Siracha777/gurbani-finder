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
st.markdown("**Paste Gurmukhi text and find it in Guru Granth Sahib Ji**")
st.markdown("---")

# ===== SEARCH INPUT =====
st.markdown("### Paste Gurmukhi Text Below")
st.markdown("💡 **How to get Gurmukhi text:**")
st.markdown("1. Record Gurbani on your phone or find lyrics online")
st.markdown("2. Use a Gurmukhi keyboard app to type what you hear")
st.markdown("3. Copy and paste here")

search_text = st.text_area(
    "Enter Gurmukhi text:",
    placeholder="ਗਹਿ ਭੁਜਾ ਲੀਨੇ. ਦਇਆ ਕੀਨੇ; ਆਪਨੇ ਕਰਿ ਮਾਨਿਆ ॥",
    height=100,
    label_visibility="collapsed"
)

# ===== SEARCH BUTTON =====
if st.button("🔍 Find in Guru Granth Sahib", type="primary", use_container_width=True):
    if search_text.strip():
        with st.spinner("Searching..."):
            results = search_gurbani(search_text, limit=15)
        
        st.markdown("---")
        
        if results:
            st.success(f"✅ Found {len(results)} match(es)!")
            st.markdown("")
            
            for i, result in enumerate(results, 1):
                sim_pct = int(result['similarity'] * 100)
                
                # Color indicator
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
            st.warning("❌ No matches found")
            st.info("💡 Try searching for a shorter phrase or different words from what you heard")
    else:
        st.warning("Please enter Gurmukhi text to search")

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
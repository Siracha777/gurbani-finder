"""
COMPLETE GURBANI APP - Improved Version
========================================
Audio → Devanagari → Gurmukhi → Search Database → Display Results
"""

import json
import os
import re
from faster_whisper import WhisperModel
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# ===== CONFIGURATION =====
GURBANI_DB = "gurbani.json"
OUTPUT_DIR = "output"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 70)
print("🙏 GURBANI LIVE TRANSCRIPTION & SCRIPTURE FINDER")
print("=" * 70)

# Check if database exists
if not os.path.exists(GURBANI_DB):
    print(f"❌ ERROR: {GURBANI_DB} not found!")
    print("Please run convert_to_json.py first.")
    exit()

print(f"✅ Database loaded: {GURBANI_DB}")

# Load Whisper model (do this once at startup)
print("🤖 Loading Whisper model...")
whisper_model = WhisperModel("small", device="cpu")
print("✅ Model ready!\n")


def clean_gurmukhi_text(text):
    """
    Clean up transcribed Gurmukhi text by removing weird symbols
    and normalizing it for better search
    """
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    
    # Remove common transcription artifacts
    text = text.replace('्', '')  # Remove halant marks that shouldn't be there
    
    # Keep only valid Gurmukhi characters and spaces
    # Gurmukhi Unicode range: U+0A00 to U+0A7F
    cleaned = ''.join(char for char in text if '\u0A00' <= char <= '\u0A7F' or char.isspace())
    
    return cleaned.strip()


def clean_audio_file(input_file, output_file="cleaned_audio.wav"):
    """Clean audio file to improve transcription quality"""
    print(f"🎧 Cleaning audio for better transcription...")
    
    try:
        from pydub import AudioSegment
        from pydub.effects import normalize
        import noisereduce as nr
        import soundfile as sf
        import librosa
        import numpy as np
        from scipy import signal
        
        # Load and convert
        audio = AudioSegment.from_file(input_file)
        if audio.channels > 1:
            audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        audio = normalize(audio)
        temp_wav = "temp_audio.wav"
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

        print(f"   ✅ Audio cleaned and saved as {output_file}")
        return output_file
        
    except ImportError as e:
        print(f"   ⚠️  Audio cleaning libraries not installed: {e}")
        print(f"   Using original audio without cleaning...")
        return input_file


def transcribe_audio_to_devanagari(audio_file_path):
    """
    Convert audio to Devanagari (Hindi script) text
    """
    print(f"🎤 Transcribing: {audio_file_path}")
    
    segments, info = whisper_model.transcribe(audio_file_path, language="pa")
    
    print(f"   Language detected: {info.language}")
    
    # Collect all segments
    transcription_text = ""
    for segment in segments:
        transcription_text += segment.text + " "
    
    transcription_text = transcription_text.strip()
    
    # Save to file
    devanagari_file = os.path.join(OUTPUT_DIR, 'transcribed.txt')
    with open(devanagari_file, 'w', encoding='utf-8') as f:
        f.write(transcription_text)
    
    # Show preview
    preview = transcription_text[:80] + "..." if len(transcription_text) > 80 else transcription_text
    print(f"   Devanagari: {preview}")
    
    return transcription_text


def convert_devanagari_to_gurmukhi(devanagari_text):
    """
    Convert Devanagari (Hindi) text to Gurmukhi script
    """
    print(f"🔄 Converting to Gurmukhi...")
    
    gurmukhi_text = transliterate(
        devanagari_text, 
        sanscript.DEVANAGARI, 
        sanscript.GURMUKHI
    )
    
    # Clean up the text
    gurmukhi_text = clean_gurmukhi_text(gurmukhi_text)
    
    # Save to file
    gurmukhi_file = os.path.join(OUTPUT_DIR, 'transcribed_gurmukhi.txt')
    with open(gurmukhi_file, 'w', encoding='utf-8') as f:
        f.write(gurmukhi_text)
    
    # Show preview
    preview = gurmukhi_text[:80] + "..." if len(gurmukhi_text) > 80 else gurmukhi_text
    print(f"   Gurmukhi: {preview}")
    
    return gurmukhi_text


def search_gurbani(query_text, limit=10):
    """
    Search for Gurmukhi text in the database with better matching
    """
    print(f"🔍 Searching for best matches...")
    
    with open(GURBANI_DB, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    results = []
    
    # Clean query text
    query_text = clean_gurmukhi_text(query_text)
    
    # Split into words (ignore very short words)
    query_words = [w for w in query_text.split() if len(w) > 2]
    
    if not query_words:
        print("   ⚠️  No meaningful words found in transcription")
        return []
    
    print(f"   Searching for: {', '.join(query_words[:5])}{'...' if len(query_words) > 5 else ''}")
    
    for record in data:
        gurmukhi = record.get("gurmukhi", "")
        
        # Count matching words
        match_score = sum(1 for word in query_words if word in gurmukhi)
        
        if match_score > 0:
            # Get English translation
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
            
            # Get Punjabi translation
            punjabi_trans = ""
            if "pa" in translations_dict:
                pa_list = translations_dict["pa"]
                if pa_list and len(pa_list) > 0:
                    punjabi_trans = pa_list[0]["text"]
            
            results.append({
                "gurmukhi": gurmukhi,
                "english": english_trans,
                "punjabi": punjabi_trans,
                "page": record.get("page"),
                "line": record.get("line"),
                "asset": record.get("asset"),
                "match_score": match_score
            })
    
    # Sort by match score (best matches first)
    results.sort(key=lambda x: x['match_score'], reverse=True)
    
    return results[:limit]


def display_results(results):
    """
    Pretty print the search results - CLEANER VERSION
    """
    print("\n" + "=" * 70)
    print("📖 RESULTS")
    print("=" * 70)
    
    if not results:
        print("\n❌ No matches found")
        print("\n💡 This could mean:")
        print("   • Audio quality is too low")
        print("   • Background noise interfering")
        print("   • The audio isn't from Guru Granth Sahib Ji")
        print("   • Try recording in a quieter environment")
        return
    
    print(f"\n✅ Found {len(results)} possible match(es)\n")
    
    for i, result in enumerate(results, 1):
        confidence = "⭐" * min(result['match_score'], 5)  # Show stars for confidence
        
        print(f"{i}. {confidence} (Matched {result['match_score']} word{'s' if result['match_score'] > 1 else ''})")
        print(f"   ✨ {result['gurmukhi']}")
        if result['english']:
            print(f"   🇬🇧 {result['english']}")
        print(f"   📄 Ang {result['page']}, Line {result['line']}")
        print()


def process_gurbani_audio(audio_file_path, use_audio_cleaning=True):
    """
    Complete workflow: Audio → Clean → Transcribe → Convert → Search → Display
    
    Parameters:
    - audio_file_path: Path to audio file
    - use_audio_cleaning: If True, cleans audio before transcription (default: True)
    """
    print("\n" + "=" * 70)
    print("🎵 PROCESSING AUDIO")
    print("=" * 70)
    print(f"📁 {audio_file_path}\n")
    
    # Check file exists
    if not os.path.exists(audio_file_path):
        print(f"❌ File not found: {audio_file_path}")
        return None
    
    # Step 0: Clean audio (optional but recommended)
    if use_audio_cleaning:
        print("STEP 0: Audio Cleaning")
        print("-" * 70)
        cleaned_audio_path = os.path.join(OUTPUT_DIR, "cleaned_audio.wav")
        audio_to_transcribe = clean_audio_file(audio_file_path, cleaned_audio_path)
        print()
    else:
        audio_to_transcribe = audio_file_path
        print("⏭️  Skipping audio cleaning (use_audio_cleaning=False)\n")
    
    # Step 1: Transcribe
    print("STEP 1: Transcribing Audio")
    print("-" * 70)
    devanagari_text = transcribe_audio_to_devanagari(audio_to_transcribe)
    
    if not devanagari_text:
        print("❌ Transcription failed")
        return None
    
    # Step 2: Convert
    print("\nSTEP 2: Converting to Gurmukhi")
    print("-" * 70)
    gurmukhi_text = convert_devanagari_to_gurmukhi(devanagari_text)
    
    if not gurmukhi_text:
        print("❌ Conversion failed")
        return None
    
    # Step 3: Search
    print("\nSTEP 3: Searching Database")
    print("-" * 70)
    results = search_gurbani(gurmukhi_text, limit=5)
    
    # Step 4: Display
    display_results(results)
    
    print("=" * 70)
    print("✅ DONE")
    print("=" * 70)
    print(f"💾 Files saved in '{OUTPUT_DIR}/' folder")
    if use_audio_cleaning:
        print(f"   • cleaned_audio.wav (cleaned audio)")
    print(f"   • transcribed.txt (Devanagari)")
    print(f"   • transcribed_gurmukhi.txt (Gurmukhi)")
    
    return results


def search_direct(gurmukhi_text):
    """
    Search directly with Gurmukhi text (for testing)
    """
    print("\n" + "=" * 70)
    print("🔤 DIRECT SEARCH")
    print("=" * 70)
    
    results = search_gurbani(gurmukhi_text, limit=5)
    display_results(results)
    
    return results


# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    import sys
    
    print("\n" + "🌟" * 35)
    print("READY!")
    print("🌟" * 35 + "\n")
    
    # Check if user provided audio file as argument
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        print(f"Processing: {audio_file}")
        process_gurbani_audio(audio_file)
    else:
        # Default examples
        print("EXAMPLE 1: Audio File (WITH Audio Cleaning)")
        print("-" * 70)
        
        audio_file = "kirtan.m4a"
        
        if os.path.exists(audio_file):
            # Process with audio cleaning
            process_gurbani_audio(audio_file, use_audio_cleaning=True)
        else:
            print(f"⚠️  '{audio_file}' not found")
            print("To process audio, run:")
            print(f"   python {sys.argv[0]} your_audio.m4a\n")
        
        print("\n\nEXAMPLE 2: Direct Search")
        print("-" * 70)
        search_direct("ਵਾਹਿਗੁਰੂ")
    
    print("\n" + "=" * 70)
    print("💡 USAGE:")
    print("=" * 70)
    print(f"""
    Process audio file (with cleaning):
        python {sys.argv[0]} your_audio.m4a
    
    Or use in code:
        # With audio cleaning (recommended)
        results = process_gurbani_audio("audio.m4a", use_audio_cleaning=True)
        
        # Without audio cleaning (faster but less accurate)
        results = process_gurbani_audio("audio.m4a", use_audio_cleaning=False)
        
        # Direct text search
        results = search_direct("ਵਾਹਿਗੁਰੂ")
    """)
    print("=" * 70)
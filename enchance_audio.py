"""
AUDIO CLEANING - Improve transcription by cleaning audio first
================================================================
This cleans the ACTUAL AUDIO FILE to improve Whisper's accuracy
"""

import os

# You'll need these libraries:
# pip install pydub noisereduce soundfile librosa numpy

from pydub import AudioSegment
from pydub.effects import normalize
import noisereduce as nr
import soundfile as sf
import librosa
import numpy as np

def clean_audio_file(input_file, output_file="cleaned_audio.wav"):
    """
    Clean audio file to improve transcription quality
    
    Steps:
    1. Convert to WAV (better for processing)
    2. Normalize volume (make consistent)
    3. Remove background noise
    4. Enhance speech frequencies
    """
    
    print("=" * 70)
    print("🎧 AUDIO CLEANING")
    print("=" * 70)
    print(f"📁 Input: {input_file}")
    
    # ===== STEP 1: Convert to WAV =====
    print("\nSTEP 1: Converting to WAV format")
    print("-" * 70)
    
    # Load audio (works with m4a, mp3, etc.)
    audio = AudioSegment.from_file(input_file)
    
    # Convert to mono (single channel - better for speech)
    if audio.channels > 1:
        print("   Converting stereo → mono")
        audio = audio.set_channels(1)
    
    # Set sample rate to 16kHz (optimal for Whisper)
    print("   Setting sample rate to 16kHz")
    audio = audio.set_frame_rate(16000)
    
    # Save as temporary WAV
    temp_wav = "temp_audio.wav"
    audio.export(temp_wav, format="wav")
    print(f"   ✅ Converted to WAV")
    
    # ===== STEP 2: Normalize Volume =====
    print("\nSTEP 2: Normalizing volume")
    print("-" * 70)
    
    # Normalize audio (make consistent volume)
    audio_normalized = normalize(audio)
    audio_normalized.export(temp_wav, format="wav")
    print("   ✅ Volume normalized")
    
    # ===== STEP 3: Remove Noise =====
    print("\nSTEP 3: Removing background noise")
    print("-" * 70)
    
    # Load audio as numpy array
    audio_data, sample_rate = librosa.load(temp_wav, sr=16000)
    
    # Apply noise reduction
    # This removes constant background noise (fan, hum, etc.)
    reduced_noise = nr.reduce_noise(
        y=audio_data,
        sr=sample_rate,
        stationary=True,  # For constant noise
        prop_decrease=0.8  # How much to reduce (0-1)
    )
    
    print("   ✅ Noise reduced")
    
    # ===== STEP 4: Enhance Speech Frequencies =====
    print("\nSTEP 4: Enhancing speech clarity")
    print("-" * 70)
    
    # Apply high-pass filter (remove very low frequencies - rumble)
    from scipy import signal
    
    # High-pass filter at 80 Hz (removes rumble)
    sos = signal.butter(5, 80, 'hp', fs=sample_rate, output='sos')
    filtered_audio = signal.sosfilt(sos, reduced_noise)
    
    # Low-pass filter at 8000 Hz (remove high-frequency noise)
    sos = signal.butter(5, 8000, 'lp', fs=sample_rate, output='sos')
    filtered_audio = signal.sosfilt(sos, filtered_audio)
    
    print("   ✅ Speech frequencies enhanced")
    
    # ===== STEP 5: Save Cleaned Audio =====
    print("\nSTEP 5: Saving cleaned audio")
    print("-" * 70)
    
    # Normalize to prevent clipping
    filtered_audio = filtered_audio / np.max(np.abs(filtered_audio))
    
    # Save cleaned audio
    sf.write(output_file, filtered_audio, sample_rate)
    
    # Clean up temp file
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
    
    print(f"   ✅ Saved to: {output_file}")
    
    print("\n" + "=" * 70)
    print("✅ AUDIO CLEANING COMPLETE!")
    print("=" * 70)
    print(f"🎤 Original: {input_file}")
    print(f"✨ Cleaned:  {output_file}")
    print("\nNow transcribe the cleaned file for better results!")
    
    return output_file


def simple_audio_cleanup(input_file, output_file="cleaned_simple.wav"):
    """
    Simpler version - just normalize and convert
    (If you don't have all the libraries installed)
    """
    print("🎧 Simple Audio Cleanup")
    print("-" * 70)
    
    # Load and normalize
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_channels(1)  # Mono
    audio = audio.set_frame_rate(16000)  # 16kHz
    audio_normalized = normalize(audio)
    
    # Save
    audio_normalized.export(output_file, format="wav")
    
    print(f"✅ Cleaned audio saved: {output_file}")
    return output_file


# ===== USAGE EXAMPLE =====
if __name__ == "__main__":
    print("\n🌟" * 35)
    print("AUDIO CLEANER FOR BETTER TRANSCRIPTION")
    print("🌟" * 35 + "\n")
    
    input_audio = "kirtan.m4a"
    
    if not os.path.exists(input_audio):
        print(f"❌ Audio file not found: {input_audio}")
        print("Please update 'input_audio' variable with your file path")
    else:
        # Try full cleanup
        try:
            cleaned_file = clean_audio_file(input_audio, "kirtan_cleaned.wav")
            
            print("\n" + "=" * 70)
            print("💡 NEXT STEP:")
            print("=" * 70)
            print(f"""
            Now transcribe the cleaned audio:
            
            In your main app, change:
                process_gurbani_audio("kirtan.m4a")
            To:
                process_gurbani_audio("{cleaned_file}")
            
            This should give you much better transcription results!
            """)
            
        except ImportError as e:
            print(f"\n⚠️  Missing library: {e}")
            print("\nTrying simple cleanup instead...")
            cleaned_file = simple_audio_cleanup(input_audio)
            
            print("\n💡 For better results, install:")
            print("   pip install noisereduce soundfile librosa scipy")
    
    print("=" * 70)
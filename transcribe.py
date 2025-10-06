from faster_whisper import WhisperModel
import os

# === AUDIO CLEANUP SECTION ===
from pydub import AudioSegment
from pydub.effects import normalize
import noisereduce as nr
import soundfile as sf
import librosa
import numpy as np
from scipy import signal

def clean_audio_file(input_file, output_file="cleaned_audio.wav"):
    """Clean audio file to improve transcription quality"""
    print("=" * 70)
    print("🎧 CLEANING AUDIO FOR BETTER TRANSCRIPTION")
    print("=" * 70)
    
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
    from scipy import signal

    # High-pass filter at 80 Hz (removes rumble)
    sos = signal.butter(5, 80, 'hp', fs=sr, output='sos')
    filtered_audio = signal.sosfilt(sos, reduced_noise)

    # Low-pass filter just below Nyquist (fs/2)
    lowpass_cutoff = 0.49 * sr  # slightly below fs/2 to avoid ValueError
    sos = signal.butter(5, lowpass_cutoff, 'lp', fs=sr, output='sos')
    filtered_audio = signal.sosfilt(sos, filtered_audio)

    # Normalize to prevent clipping
    filtered_audio = filtered_audio / np.max(np.abs(filtered_audio))
    sf.write(output_file, filtered_audio, sr)
    if os.path.exists(temp_wav):
        os.remove(temp_wav)

    print(f"✅ Cleaned audio saved as {output_file}")
    return output_file


# === TRANSCRIPTION SECTION ===
def transcribe_audio(audio_file, output_txt="output/transcribed.txt"):
    """Transcribe audio and save text"""
    print("=" * 70)
    print("🧠 TRANSCRIBING AUDIO")
    print("=" * 70)

    model = WhisperModel("small", device="cpu")
    segments, info = model.transcribe(audio_file, language="pa")

    print("Detected language:", info.language)
    print("Transcription:")

    # Collect segments
    transcription_text = ""
    for segment in segments:
        print(segment.text)
        transcription_text += segment.text + " "

    os.makedirs(os.path.dirname(output_txt), exist_ok=True)
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(transcription_text.strip())

    print(f"\n✅ Transcription saved to {output_txt}")
    return transcription_text


# === MAIN SCRIPT ===
if __name__ == "__main__":
    input_audio = "kirtan.m4a"
    cleaned_audio = "kirtan_cleaned.wav"

    # Step 1: Clean audio
    cleaned_path = clean_audio_file(input_audio, cleaned_audio)

    # Step 2: Transcribe cleaned audio
    transcribe_audio(cleaned_path)

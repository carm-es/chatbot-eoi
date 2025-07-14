import subprocess
import tempfile

from google.cloud import speech_v1p1beta1 as speech
from utils.translate import translate_text


speech_client = speech.SpeechClient()

def transcribe_and_translate(file):
    """
    Transcribes an audio file and translates it into Spanish if it is in another language.
    Supports: Spanish, English, French, German, Italian, Chinese, Arabic, Japanese

    Args:
        file : Audio of the user

    Returns:
        str: Audio transcribed in spanish
    """
    input_filename = getattr(file, 'filename', None)
    if input_filename and input_filename.lower().endswith('.webm'):
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_in, \
             tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_out:
            temp_in.write(file.file.read())
            temp_in.flush()
            subprocess.run([
                'ffmpeg', '-y', '-i', temp_in.name,
                '-ar', '16000', '-ac', '1', '-f', 'wav', temp_out.name
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            temp_out.seek(0)
            audio_content = temp_out.read()
    else:
        audio_content = file.file.read()

    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="es-ES",
        enable_automatic_punctuation=True,
        enable_spoken_punctuation=True,
        enable_spoken_emojis=True,
        alternative_language_codes=[
            "en-US",  # English
            "fr-FR",  # French
            "de-DE",  # German
            "it-IT",  # Italian
            "zh-CN",  # Chinese (Simplified)
            "ar-SA",  # Arabic
            "ja-JP"   # Japanese
        ]
    )
    
    response = speech_client.recognize(config=config, audio=audio)
    transcript = ""
    detected_language = "es"
    
    for result in response.results:
        transcript += result.alternatives[0].transcript
        if result.language_code:
            detected_language = result.language_code[:2]
    
    if detected_language != "es":
        transcript = translate_text(transcript, "es")
    
    return transcript
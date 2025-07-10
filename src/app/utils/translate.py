from google.cloud import translate_v2 as translate
import html

translate_client = translate.Client()

def detect_language(text):
    result = translate_client.detect_language(text)
    return result['language']

def translate_text(text, target_language):
    if not text:
        return text
    # Usar español como idioma por defecto si target_language es 'und', vacío o None
    if not target_language or target_language == 'und':
        target_language = 'es'
    result = translate_client.translate(text, target_language=target_language)
    return result['translatedText']

def unescape_html(text):
    """
    Decodes HTML entities in a string (e.g., &#39; to ').
    Args:
        text (str): The text to decode.
    Returns:
        str: The decoded text.
    """
    return html.unescape(text) 
from google.cloud import translate_v2 as translate
import html

translate_client = translate.Client()

def detect_language(text):
    result = translate_client.detect_language(text)
    return result['language']

def translate_text(text, target_language):
    if not text:
        return text
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

def detect_language_ranking(text):
    """
    Devuelve un ranking de posibles idiomas detectados para el texto, con su confianza.
    Prioriza español ('es'), luego italiano ('it'), luego el resto según confianza.
    """
    result = translate_client.detect_language([text])
    if result and isinstance(result, list) and len(result) > 0:
        detections = result[0]
        es = [d for d in detections if d.get('language') == 'es']
        it = [d for d in detections if d.get('language') == 'it']
        others = [d for d in detections if d.get('language') not in ('es', 'it')]
        others_sorted = sorted(others, key=lambda d: d.get('confidence', 0), reverse=True)
        ranking = es + it + others_sorted
        return [
            {'language': d.get('language'), 'confidence': d.get('confidence', 0)}
            for d in ranking
        ]
    return [] 
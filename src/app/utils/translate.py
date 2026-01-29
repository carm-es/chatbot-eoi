import re
import html
from google.cloud import translate_v2 as translate
from collections import Counter, defaultdict

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


def detectar_aparicion_escuela( texto: str ):
    """
    Devuelve un ranking de ocurrencias de nombres de eois y extensiones
    """
    texto = texto.lower()
    mapa_topico_palabras = {
        "caravaca de la cruz": ["caravaca"],
        "cartagena": ["cartagena"],
        "fuente álamo": ["álamo", "alamo"],
        "mazarrón": ["mazarrón", "mazarron"],
        "águilas": ["águilas", "aguilas"],
        "totana": ["totana"],
        "alhama": ["alhama"],
        "puerto lumbreras": ["lumbreras"],
        "archena": ["archena"],
        "cieza": ["cieza"],
        "yecla": ["yecla"],
        "jumilla": ["jumilla"],
        "murcia": ["murcia"],
        "alcantarilla": ["alcantarilla"],
        "infante": ["infante"],
        "santomera": ["santomera"],
        "san javier": ["javier"],
        "lorca": ["lorca"],
        "molina de segura": ["segura", "molina"],
        "torre pacheco": ["pacheco"],
    }

    palabra_a_topicos = defaultdict(dict)

    for topico, palabras in mapa_topico_palabras.items():

        # Caso: lista de palabras (peso = 1)
        if isinstance(palabras, list):
            for palabra in palabras:
                palabra_a_topicos[palabra.lower()][topico] = 1

        # Caso: dict palabra -> peso
        elif isinstance(palabras, dict):
            for palabra, peso in palabras.items():
                palabra_a_topicos[palabra.lower()][topico] = peso

        else:
            raise ValueError(
                f"Formato no soportado en el tópico '{topico}'"
            )

    tokens = re.findall(r'\b\w+\b', texto)

    conteo_palabras = Counter()
    conteo_topicos = Counter()

    for token in tokens:
        if token not in palabra_a_topicos:
            continue

        conteo_palabras[token] += 1

        for topico, peso in palabra_a_topicos[token].items():
            conteo_topicos[topico] += peso

    if not conteo_topicos:
        return {}, {}, []

    max_score = max(conteo_topicos.values())
    topicos_top = [
        topico for topico, score in conteo_topicos.items()
        if score == max_score
    ]

    return dict(conteo_palabras), dict(conteo_topicos), topicos_top


def detectar_escuela( texto: str ):
    try:
        palabras, topicos, top = detectar_aparicion_escuela(texto)
        return top[0] if top else ""
    except Exception as e:
        return ""

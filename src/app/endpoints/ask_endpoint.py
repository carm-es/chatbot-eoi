from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from typing import Dict
from pydantic import BaseModel
from services import speech_to_text, conversation_agent, big_query
from utils.translate import detect_language, translate_text, unescape_html
import requests

import logging

MAX_NUM_WORDS=4
DEFAULT_LANGUAGE='es'

router = APIRouter()


def get_client_info(request: Request) -> Dict[str, str]:
    def get_real_ip():
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host

    return {
        "ip": get_real_ip(),
        "user_agent": request.headers.get("user-agent", "Desconocido"),
        "host": request.headers.get("host", "Desconocido"),
        "referer": request.headers.get("referer", "Directo")
    }

@router.post('/ask/text')
async def ask_text(message: str = Form(...), session_id: str = Form(None), language: str = Form(None), client_info: Dict[str, str] = Depends(get_client_info) ):

    logging.info(f"Petición desde IP: {client_info['ip']}, User-Agent: {client_info['user_agent']}, HOST: {client_info['host']} , Referer: {client_info['referer']}")

    """
    Endpoint to send text messages to the agent.

    Args:
        message (str): Message from the user.
        session_id (str, optional): Session ID for the conversation.
        language (str, optional): Preferred language for the response.

    Returns:
        dict: "response" with the agent's reply in the user's language and "session_id".
    """

    ## Detectar idioma solo cuando haya mas X palabras
    num_words = len(message.split())
    detected_language = "und"
    if num_words > MAX_NUM_WORDS:
        detected_language = detect_language(message)

    if not language or language == 'und':
        if num_words <= MAX_NUM_WORDS:
            input_language = DEFAULT_LANGUAGE
        else:
            input_language = detected_language
    elif detected_language == 'und':
        input_language = language
    elif language != detected_language and num_words > MAX_NUM_WORDS:
        input_language = detected_language
    else:
        input_language = language

    if input_language == 'und':
        input_language = DEFAULT_LANGUAGE

    logging.info(f"Pregunta original: '{message}' | Idioma detectado: {detected_language} | Idioma usado: {input_language}")
    message_es = translate_text(message, DEFAULT_LANGUAGE) if input_language != DEFAULT_LANGUAGE else message

    logging.info(f"Pregunta en español enviada para Dialogflow: '{message_es}'")
    response_data = conversation_agent.send_message(message_es, session_id)
    response_es = response_data["message"]
    session_id = response_data["session_id"]
    response_id = response_data["response_id"]
    dialogflow_code = response_data["code_result"]
    raw_resp = response_data["raw_response"]

    logging.info(f"Respuesta en español de Dialogflow: '{response_es}' y '{raw_resp}'")

    final_response = translate_text(response_es, input_language)
    final_response = unescape_html(final_response)
    logging.info(f"Session ID: {session_id} - Response ID: {response_id}")

    await big_query.insert_interaction(
        session_id=session_id,
        interaction_id=response_id,
        source="Página web",
        user_input=message,
        language=input_language,
        dialog_response=final_response,
        code=dialogflow_code
    )
    return {"response": final_response, "session_id": session_id, "response_id": response_id, "language": input_language}

@router.post('/ask/voice')
async def ask_voice(file: UploadFile = File(...), session_id: str = Form(None), language: str = Form(None)):
    """
    Endpoint to send voice messages to the agent.

    Args:
        file (UploadFile): Audio from the user.
        session_id (str, optional): Session ID for the conversation.
        language (str, optional): Preferred language for the response.

    Returns:
        dict: "response" with the agent's reply in the user's language and "session_id".
    """
    text = speech_to_text.transcribe_and_translate(file)

    ## Detectar idioma solo cuando haya mas X palabras
    num_words = len(text.split())
    detected_language = "und"
    if num_words > MAX_NUM_WORDS:
        detected_language = detect_language(text)

    if not language or language == 'und':
        if num_words <= MAX_NUM_WORDS:
            input_language = DEFAULT_LANGUAGE
        else:
            input_language = detected_language
    elif detected_language == 'und':
        input_language = language
    elif language != detected_language and num_words > MAX_NUM_WORDS:
        input_language = detected_language
    else:
        input_language = language

    if input_language == 'und':
        input_language = DEFAULT_LANGUAGE

    logging.info(f"Pregunta original (voz): '{text}' | Idioma detectado: {detected_language} | Idioma usado: {input_language}")

    text_es = translate_text(text, DEFAULT_LANGUAGE) if input_language != DEFAULT_LANGUAGE else text
    logging.info(f"Pregunta en español enviada a Dialogflow: '{text_es}'")

    response_data = conversation_agent.send_message(text_es, session_id)
    response_es = response_data["message"]
    session_id = response_data["session_id"]
    response_id = response_data["response_id"]
    logging.info(f"Respuesta en español de Dialogflow: '{response_es}'")

    final_response = translate_text(response_es, input_language)
    final_response = unescape_html(final_response)
    logging.info(f"Session ID: {session_id} - Response ID: {response_id}")

    await big_query.insert_interaction(
        session_id=session_id,
        interaction_id=response_id,
        source="Página web",
        user_input=text,
        language=input_language,
        dialog_response=final_response
    )
    return {"response": final_response, "session_id": session_id, "response_id": response_id, "language": input_language}

class RateRequest(BaseModel):
    response_id: str
    valoration: str = None
    description: str = None
    session_id: str

@router.post('/rate')
async def rate_response(rate_request: RateRequest):
    """
    Endpoint para manejar el feedback de los usuarios sobre las respuestas.
    """
    if (rate_request.valoration and rate_request.description) or (not rate_request.valoration and not rate_request.description):
        return {"error": "Debes proporcionar solo uno de los campos: valoration o description, pero nunca ambos ni ninguno."}

    if rate_request.valoration and rate_request.valoration not in ['like', 'dislike']:
        return {"error": "La valoración debe ser 'like' o 'dislike' si se proporciona"}
    
    logging.info(f"Feedback recibido - Response ID: {rate_request.response_id}, Valoración: {rate_request.valoration}")
    if rate_request.description:
        logging.info(f"Descripción adicional: {rate_request.description}")
    
    await big_query.add_rating(
        session_id=rate_request.session_id,
        interaction_id=rate_request.response_id,
        rating=rate_request.valoration,
        feedback=rate_request.description
    )
    return {
        "message": "Feedback recibido correctamente",
        "response_id": rate_request.response_id,
        "valoration": rate_request.valoration,
        "description": rate_request.description
    }

@router.post('/cambio-grupo')
async def cambio_grupo(nre: int = Form(...)):
    url = "http://chatbot-eoi.murciaeduca.es/peticiones/index.php"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    data = {"accion": "cambio-de-grupo", "NRE": int(nre)}
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        logging.info(f"Respuesta recibida: status_code={response.status_code}, contenido={response.text}")
        if response.status_code == 200:
            return {"result": "ok"}
        else:
            return {"result": "error"}
    except Exception as e:
        logging.error(f"Excepción al hacer la petición: {e}")
        return {"result": "error"}

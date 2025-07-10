from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from services import speech_to_text, conversation_agent, big_query
from utils.translate import detect_language, translate_text, unescape_html

import logging

router = APIRouter()

@router.post('/ask/text')
async def ask_text(message: str = Form(...), session_id: str = Form(None)):
    """
    Endpoint to send text messages to the agent.

    Args:
        message (str): Message from the user.
        session_id (str, optional): Session ID for the conversation.

    Returns:
        dict: "response" with the agent's reply in the user's language and "session_id".
    """
    # Log de la pregunta original y el idioma detectado
    input_language = detect_language(message)
    logging.info(f"Pregunta original: '{message}' | Idioma detectado: {input_language}")
    message_es = translate_text(message, 'es') if input_language != 'es' else message
    # Log de la pregunta en español enviada a Dialogflow
    logging.info(f"Pregunta en español enviada a Dialogflow: '{message_es}'")
    response_data = conversation_agent.send_message(message_es, session_id)
    response_es = response_data["message"]
    session_id = response_data["session_id"]
    response_id = response_data["response_id"]
    # Log de la respuesta en español de Dialogflow
    logging.info(f"Respuesta en español de Dialogflow: '{response_es}'")
    final_response = (
        translate_text(response_es, input_language)
        if input_language != 'es' else response_es
    )
    final_response = unescape_html(final_response)
    # Log de la respuesta final en el idioma del usuario
    logging.info(f"Session ID: {session_id} - Response ID: {response_id}")
    # Guardar interacción en BigQuery
    await big_query.insert_interaction(
        session_id=session_id,
        interaction_id=response_id,
        source="Página web",
        user_input=message,
        language=input_language,
        dialog_response=final_response
    )
    return {"response": final_response, "session_id": session_id, "response_id": response_id}

@router.post('/ask/voice')
async def ask_voice(file: UploadFile = File(...), session_id: str = Form(None)):
    """
    Endpoint to send voice messages to the agent.

    Args:
        file (UploadFile): Audio from the user.
        session_id (str, optional): Session ID for the conversation.

    Returns:
        dict: "response" with the agent's reply in the user's language and "session_id".
    """
    text = speech_to_text.transcribe_and_translate(file)
    input_language = detect_language(text)
    # Log de la pregunta original y el idioma detectado
    logging.info(f"Pregunta original (voz): '{text}' | Idioma detectado: {input_language}")
    text_es = translate_text(text, 'es') if input_language != 'es' else text
    # Log de la pregunta en español enviada a Dialogflow
    logging.info(f"Pregunta en español enviada a Dialogflow: '{text_es}'")
    response_data = conversation_agent.send_message(text_es, session_id)
    response_es = response_data["message"]
    session_id = response_data["session_id"]
    response_id = response_data["response_id"]
    # Log de la respuesta en español de Dialogflow
    logging.info(f"Respuesta en español de Dialogflow: '{response_es}'")
    final_response = (
        translate_text(response_es, input_language)
        if input_language != 'es' else response_es
    )
    final_response = unescape_html(final_response)
    # Log de la respuesta final en el idioma del usuario
    logging.info(f"Session ID: {session_id} - Response ID: {response_id}")
    # Guardar interacción en BigQuery
    await big_query.insert_interaction(
        session_id=session_id,
        interaction_id=response_id,
        source="Página web",
        user_input=text,
        language=input_language,
        dialog_response=final_response
    )
    return {"response": final_response, "session_id": session_id, "response_id": response_id}

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
    # Validar que se reciba exactamente uno de los dos campos: valoration o description
    if (rate_request.valoration and rate_request.description) or (not rate_request.valoration and not rate_request.description):
        return {"error": "Debes proporcionar solo uno de los campos: valoration o description, pero nunca ambos ni ninguno."}

    # Validar que la valoración sea válida si se proporciona
    if rate_request.valoration and rate_request.valoration not in ['like', 'dislike']:
        return {"error": "La valoración debe ser 'like' o 'dislike' si se proporciona"}
    
    # Log del feedback recibido
    logging.info(f"Feedback recibido - Response ID: {rate_request.response_id}, Valoración: {rate_request.valoration}")
    if rate_request.description:
        logging.info(f"Descripción adicional: {rate_request.description}")
    
    # Guardar valoración en BigQuery
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

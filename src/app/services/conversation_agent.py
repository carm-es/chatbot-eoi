import os
import uuid
import time
import random
import logging
from dotenv import load_dotenv
from typing import Dict
from datetime import datetime
from google.cloud import dialogflowcx_v3beta1 as dialogflowcx


load_dotenv()

# Config of the agent
PROJECT_ID = os.getenv('DIALOGFLOW_PROJECT_ID')
LOCATION = os.getenv('DIALOGFLOW_LOCATION')
AGENT_ID = os.getenv('AGENT_ID')

NOT_FOUND = ["Lo siento, pero no tengo información suficiente para poder responderte",
             "Disculpa mis limitaciones, no tengo información suficiente para responderte",
             "Perdona, no dispongo de información para poder resolver tu duda",
             "Lamento no poder responder a tu pregunta. Carezco de información suficiente para poder responderte, pero puedo ayudarte con otras consultas",
             "¡Vaya! Parece que no tengo datos para poder responderte. ¿Quieres que te ayude con algo relacionado o más general?",
             "Disculpa, pero no acierto a resolver tu pregunta. ¿Podrías reformularla o darme más detalles, a ver si tengo más suerte?",
             "Gracias por tu pregunta, pero aún no tengo recursos para responderla, trataremos de solucionarlo ¿en qué más puedo asistirte?",
             "¡Ups! No tengo información sobre eso. ¿Necesitas ayuda con otro tema?", 
             "Lo siento, no dispongo de esa información",
             "Ahora mismo no tengo datos para responder, pero me actualizan constantemente, pregúntame algo más a ver como sale 😅"]

session_client = dialogflowcx.SessionsClient()

def get_current_month():
    MESES_ES = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    return MESES_ES[datetime.now().month - 1]


def get_response_info(message: str) -> Dict[str, str]:
    def get_result_code():
        if "NOT FOUND" in message:
            return "NOT_FOUND"
        if not message:
            return "NOT_FOUND"
        return "OK"

    def get_response():
        if "NOT FOUND" in message:
            return random.choice(NOT_FOUND)
        if not message:
            return random.choice(NOT_FOUND)
        return message

    return {
        "raw": message,
        "result": get_result_code(),
        "response": get_response()
    }

def send_message(text: str, session_id: str = None, school: str = "murcia" ):
    """
    Send the message to the agent

    Args:
        text (str): A message to the agent of Dialogflow
        session_id (str, optional): Session ID for the conversation. If None, creates a new one.

    Returns:
        dict: Dictionary containing "message" and "session_id"
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    session_dlgflow = f"{session_id}-{int(time.time())}"
    session_path = session_client.session_path(PROJECT_ID, LOCATION, AGENT_ID, session_dlgflow)

    text_input = dialogflowcx.TextInput(text=text)
    query_input = dialogflowcx.QueryInput(text=text_input, language_code="es")

    # Inyectar variables de contexto
    context_params = {
        "escuela": school,
        "mes_actual": get_current_month()
    }
    query_params = dialogflowcx.QueryParameters(
        parameters=context_params,
        time_zone="Europe/Paris"
    )

    response_id = "NULL_ID"
    try:
        request = dialogflowcx.DetectIntentRequest(
            session=session_path,
            query_input=query_input,
            query_params=query_params
        )

        response = session_client.detect_intent(request=request)
        message = response.query_result.response_messages[0].text.text[0] if response.query_result.response_messages else ""
        response_id = response.response_id

        response_info = get_response_info(message)

        response_message =  response_info['response']
        response_result = response_info['result']
        response_raw = response_info['raw']

    except Exception as e:
        response_message = random.choice(NOT_FOUND)
        response_result = "ERROR"
        response_raw = f"Error en llamada a Dialogflow: {str(e)}"

    return {"message": response_message, "session_id": session_id, "response_id": response_id, "code_result": response_result, "raw_response": response_raw}


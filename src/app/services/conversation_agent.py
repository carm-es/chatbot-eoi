import os
import uuid
import time
import random
import re
import logging
from dotenv import load_dotenv
from typing import Dict
from datetime import datetime, date
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

def process_response(text: str) -> Dict[str, str]:
    contest = {}

    # Regex para los campos
    summary_match = re.search(
        r"user_summary:\s*(.*?)(?=detected_language:|$)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    lang_match = re.search(
        r"detected_language:\s*(.*?)(?=user_summary:|$)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    contest["resumen"] = summary_match.group(1).strip() if summary_match else ""
    contest["lang"] = lang_match.group(1).strip() if lang_match else ""

    message = re.sub(r"user_summary:.*?(?=detected_language:|$)", "", text, flags=re.IGNORECASE | re.DOTALL)
    message = re.sub(r"detected_language:.*?(?=user_summary:|$)", "", message, flags=re.IGNORECASE | re.DOTALL)

    contest["message"] = message.strip()

    return contest

def get_current_month():
    MESES_ES = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    hoy = date.today()
    #### mes = MESES_ES[datetime.now().month - 1]
    #### return f"{hoy.day} de {mes} de {hoy.year}"
    return f"{hoy.year:04d}-{hoy.month:02d}-{hoy.day:02d}"


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


def extract_dialogflow_text(response):
    """
    Intenta extraer el primer mensaje de texto disponible.
    Si no encuentra ninguno, levanta una excepción.
    """
    try:
        messages = response.query_result.response_messages

        if not messages:
            raise ValueError("La lista de response_messages está vacía.")

        for msg in messages:
            # Verificamos si el mensaje tiene el atributo 'text' y contiene datos
            if hasattr(msg, 'text') and msg.text.text:
                # Retornamos el primer string encontrado en la lista de textos
                return msg.text.text[0]

        # Si recorre todos los mensajes y ninguno es de texto
        raise ValueError("No se encontró ningún mensaje de tipo texto en la respuesta.")

    except (AttributeError, IndexError) as e:
        raise ValueError(f"Error de estructura al extraer el texto: '{str(e)}' del objeto '{str(response)}'")

def send_message(text: str, session_id: str = None, school: str = "murcia" , summary: str ="" ):
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
        "resumen": summary,
        "hoy": get_current_month()
    }
    query_params = dialogflowcx.QueryParameters(
        parameters=context_params,
        time_zone="Europe/Paris"
    )

    response_id = "NULL_ID"
    user_summary = ""
    user_language = ""
    try:
        request = dialogflowcx.DetectIntentRequest(
            session=session_path,
            query_input=query_input,
            query_params=query_params
        )

        response = session_client.detect_intent(request=request)
        message = extract_dialogflow_text(response)
        response_id = response.response_id

        session_params = response.query_result.parameters
        user_summary = session_params.get('user_summary', '')
        user_language = session_params.get('detected_language', '')

        response_info = get_response_info(message)

        contest = process_response(response_info['response'])
        response_message =  contest["message"]
        response_result = response_info['result']
        response_raw = response_info['raw']

        if not user_summary or user_summary == '':
            if contest["resumen"] and  contest["resumen"] != '':
                user_summary = contest["resumen"]

        if not user_language or user_language == '':
            if contest["lang"] and contest["lang"] != '':
                user_language = contest["lang"]


    except Exception as e:
        response_message = random.choice(NOT_FOUND)
        response_result = "ERROR"
        response_raw = f"Error en llamada a Dialogflow: '{str(e)}' "

    return {"message": response_message, "session_id": session_id, "response_id": response_id, "code_result": response_result, "raw_response": response_raw, "out_language": user_language, "out_summary": user_summary }


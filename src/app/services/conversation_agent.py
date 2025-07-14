import os
import uuid
import random

from dotenv import load_dotenv

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

def send_message(text: str, session_id: str = None):
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
    session_path = session_client.session_path(PROJECT_ID, LOCATION, AGENT_ID, session_id)
    
    text_input = dialogflowcx.TextInput(text=text)
    query_input = dialogflowcx.QueryInput(text=text_input, language_code="es")
    
    request = dialogflowcx.DetectIntentRequest(
        session=session_path,
        query_input=query_input
    )
    
    response = session_client.detect_intent(request=request)
    message = response.query_result.response_messages[0].text.text[0] if response.query_result.response_messages else ""
    response_id = response.response_id
    
    if "NOT FOUND" in message:
        message = random.choice(NOT_FOUND)
    
    return {"message": message, "session_id": session_id, "response_id": response_id}
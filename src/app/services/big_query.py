import logging
import os

from datetime import datetime, timezone
from dotenv import load_dotenv

from google.cloud import bigquery

client = bigquery.Client()

TABLE_ID = os.getenv("TABLE")

async def insert_interaction(session_id: str, interaction_id: str, source: str, user_input: str, language: str, dialog_response: str, code: str):
    """
    Inserta una nueva interacción en la tabla de BigQuery.
    """
    timestamp = datetime.now(timezone.utc)
    query = f"""
        INSERT INTO `{TABLE_ID}` (session_id, interaction_id, source, user_input, language, dialog_response, timestamp, dialogflow_code)
        VALUES (@session_id, @interaction_id, @source, @user_input, @language, @dialog_response, @timestamp, @dialogflow_code )
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
            bigquery.ScalarQueryParameter("interaction_id", "STRING", interaction_id),
            bigquery.ScalarQueryParameter("source", "STRING", source),
            bigquery.ScalarQueryParameter("user_input", "STRING", user_input),
            bigquery.ScalarQueryParameter("language", "STRING", language),
            bigquery.ScalarQueryParameter("dialog_response", "STRING", dialog_response),
            bigquery.ScalarQueryParameter("timestamp", "TIMESTAMP", timestamp),
            bigquery.ScalarQueryParameter("dialogflow_code", "STRING", code),
        ]
    )
    try:
        query_job = client.query(query, job_config=job_config)
        query_job.result()
        logging.info(f"Interacción insertada en BigQuery: session_id={session_id}, interaction_id={interaction_id}")
    except Exception as e:
        logging.error(f"Error insertando interacción en BigQuery: {e}")
        raise

async def add_rating(session_id: str, interaction_id: str, rating: str = None, feedback: str = None):
    """
    Actualiza la valoración o el feedback de una interacción en la tabla de BigQuery.
    Al menos uno de los dos parámetros (rating o feedback) debe estar presente.
    """
    if not rating and not feedback:
        raise ValueError("Se debe proporcionar al menos rating o feedback.")

    set_clauses = []
    params = [
        bigquery.ScalarQueryParameter("session_id", "STRING", session_id),
        bigquery.ScalarQueryParameter("interaction_id", "STRING", interaction_id),
    ]
    if rating:
        set_clauses.append("rating = @rating")
        params.append(bigquery.ScalarQueryParameter("rating", "STRING", rating))
    if feedback:
        set_clauses.append("feedback = @feedback")
        params.append(bigquery.ScalarQueryParameter("feedback", "STRING", feedback))

    set_clause = ", ".join(set_clauses)
    query = f"""
        UPDATE `{TABLE_ID}`
        SET {set_clause}
        WHERE session_id = @session_id AND interaction_id = @interaction_id
    """
    job_config = bigquery.QueryJobConfig(query_parameters=params)
    try:
        query_job = client.query(query, job_config=job_config)
        query_job.result()
        logging.info(f"Valoración/feedback actualizado en BigQuery: session_id={session_id}, interaction_id={interaction_id}")
    except Exception as e:
        logging.error(f"Error actualizando valoración/feedback en BigQuery: {e}")
        raise

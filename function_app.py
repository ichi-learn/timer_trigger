import azure.functions as func
import logging
import os
import json
import requests
from datetime import datetime
import pytz

app = func.FunctionApp()

def perform_translation(text: str, key: str, endpoint: str, region: str) -> str:
    """Calls the Azure AI Translator API to translate text from English to Japanese."""
    path = '/translate?api-version=3.0'
    # Corrected the translation direction from ja->en to en->ja
    params = '&from=en&to=ja'
    constructed_url = endpoint + path + params

    headers = {
        'Ocp-Apim-Subscription-Key': key,
        'Ocp-Apim-Subscription-Region': region,
        'Content-type': 'application/json'
    }

    body = [{'text': text}]

    try:
        response = requests.post(constructed_url, headers=headers, json=body)
        response.raise_for_status()
        translated_list = response.json()
        if translated_list and 'translations' in translated_list[0] and translated_list[0]['translations']:
            return translated_list[0]['translations'][0]['text']
        else:
            logging.error(f"Unexpected API response format: {response.text}")
            return text
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred during translation API call: {e}")
        return text
    except Exception as e:
        logging.error(f"An unexpected error occurred in perform_translation: {e}")
        return text

@app.route(route="translate")
def translate_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    text_to_translate = req.params.get('text')
    if not text_to_translate:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            text_to_translate = req_body.get('text')

    if text_to_translate:
        translator_key = os.environ.get('TRANSLATOR_KEY')
        translator_endpoint = os.environ.get('TRANSLATOR_ENDPOINT')
        translator_region = os.environ.get('TRANSLATOR_REGION')

        if not all([translator_key, translator_endpoint, translator_region]):
            logging.error("Azure AI Translator environment variables are not configured.")
            return func.HttpResponse(
                "Azure AI Translator environment variables are not configured.",
                status_code=500
            )

        translated_text = perform_translation(
            text_to_translate,
            translator_key,
            translator_endpoint,
            translator_region
        )
        return func.HttpResponse(translated_text, mimetype="text/plain; charset=utf-8")
    else:
        return func.HttpResponse(
             "Please pass a 'text' on the query string or in the request body",
             status_code=400
        )

@app.schedule(schedule="0 30 0 * * 1-5", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def daily_notifier(myTimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.utcnow().replace(tzinfo=pytz.utc).isoformat()

    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
    
    # Text to be translated
    text_to_translate = "Good morning! This is your daily notification."

    # Get environment variables
    translator_key = os.environ.get('TRANSLATOR_KEY')
    translator_endpoint = os.environ.get('TRANSLATOR_ENDPOINT')
    translator_region = os.environ.get('TRANSLATOR_REGION')
    
    if not all([translator_key, translator_endpoint, translator_region]):
        logging.error("Azure AI Translator environment variables are not configured for the daily job.")
        return
    
    translated_text = perform_translation(text_to_translate, translator_key, translator_endpoint, translator_region)
    logging.info(f"Daily translation result: '{text_to_translate}' -> '{translated_text}'")

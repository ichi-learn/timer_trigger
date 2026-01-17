import azure.functions as func
import logging
import os
import json
import requests

app = func.FunctionApp()

# Define a function that can be reused for translation logic
def perform_translation(text: str, key: str, endpoint: str, region: str) -> str:
    """Calls the Azure AI Translator API to translate text from Japanese to English."""
    path = '/translate?api-version=3.0'
    params = '&from=ja&to=en'
    constructed_url = endpoint + path + params

    headers = {
        'Ocp-Apim-Subscription-Key': key,
        'Ocp-Apim-Subscription-Region': region,
        'Content-type': 'application/json'
    }

    body = [{'text': text}]

    try:
        request = requests.post(constructed_url, headers=headers, json=body)
        request.raise_for_status()  # Raise an exception for bad status codes
        response = request.json()
        return response[0]['translations'][0]['text']
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred during translation API call: {e}")
        return "Translation failed."
    except (KeyError, IndexError) as e:
        logging.error(f"An error occurred while parsing translation response: {e}")
        return "Failed to parse translation response."

@app.route(route="translate", methods=['GET', 'POST'], auth_level=func.AuthLevel.ANONYMOUS)
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
        # Re-triggering deployment with a comment.
        translator_key = os.environ.get('TRANSLATOR_KEY')
        translator_endpoint = os.environ.get('TRANSLATOR_ENDPOINT')
        translator_region = os.environ.get('TRANSLATOR_REGION')

        if not all([translator_key, translator_endpoint, translator_region]):
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

        return func.HttpResponse(translated_text)
    else:
        return func.HttpResponse(
             "Please pass a 'text' on the query string or in the request body to translate.",
             status_code=400
        )

# This is the timer-triggered function.
@app.schedule(schedule="0 30 9 * * 1-5", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def daily_translator_job(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')
    
    # In a real scenario, you might fetch text from a DB or other source
    text_to_translate = "こんにちは"
    
    translator_key = os.environ.get('TRANSLATOR_KEY')
    translator_endpoint = os.environ.get('TRANSLATOR_ENDPOINT')
    translator_region = os.environ.get('TRANSLATOR_REGION')

    if not all([translator_key, translator_endpoint, translator_region]):
        logging.error("Azure AI Translator environment variables are not configured for the daily job.")
        return

    translated_text = perform_translation(text_to_translate, translator_key, translator_endpoint, translator_region)
    logging.info(f"Daily translation result: '{text_to_translate}' -> '{translated_text}'")

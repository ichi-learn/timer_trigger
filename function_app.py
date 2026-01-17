import azure.functions as func
import logging
import os
import requests
import json

app = func.FunctionApp()

# 1. HTTP Trigger (Translate Function)
@app.route(route="translate", auth_level=func.AuthLevel.ANONYMOUS)
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
        # Azure AI Translator environment variables
        translator_key = os.environ.get('TRANSLATOR_KEY')
        translator_endpoint = os.environ.get('TRANSLATOR_ENDPOINT')
        translator_region = os.environ.get('TRANSLATOR_REGION')

        if not all([translator_key, translator_endpoint, translator_region]):
            return func.HttpResponse(
                "Azure AI Translator environment variables are not configured.",
                status_code=500
            )

        # Call translation logic
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

# 2. Timer Trigger (Daily Notifier)
# Schedule: "0 0 9 * * *" for 9:00 AM JST (0:00 AM UTC)
# Azure Functions uses NCRONTAB which has 6 fields including seconds.
# "0 0 0 * * *" corresponds to midnight UTC.
@app.schedule(schedule="0 0 0 * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False) 
def daily_notifier(myTimer: func.TimerRequest) -> None:
    logging.info('Scheduled task started')
    
    # In a real scenario, you might fetch text from a DB or other source
    text_to_translate = "こんにちは"
    
    # Azure AI Translator environment variables
    translator_key = os.environ.get('TRANSLATOR_KEY')
    translator_endpoint = os.environ.get('TRANSLATOR_ENDPOINT')
    translator_region = os.environ.get('TRANSLATOR_REGION')

    if not all([translator_key, translator_endpoint, translator_region]):
        logging.error("Azure AI Translator environment variables are not configured for the daily notifier.")
        return

    # Call the translation logic directly.
    translated_text = perform_translation(text_to_translate, translator_key, translator_endpoint, translator_region)
    logging.info(f"Translation result: {translated_text}")
    
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')


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
        response_data = request.json()
        return response_data[0]['translations'][0]['text']
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling translator API: {e}")
        return f"Error during translation: {e}"
    except (KeyError, IndexError) as e:
        logging.error(f"Error parsing translator API response: {e}")
        return f"Error processing translation result: {e}"

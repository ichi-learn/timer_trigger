import azure.functions as func
import logging
import os
import requests

# Define global constants
TRANSLATOR_API_KEY = os.environ.get("TRANSLATOR_API_KEY")
TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com"

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="translate")
def translate(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # 1. Get text from query parameter
    text_to_translate = req.params.get('text')

    if not text_to_translate:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            text_to_translate = req_body.get('text')

    if not text_to_translate:
        return func.HttpResponse(
             "Please pass a 'text' on the query string or in the request body",
             status_code=400
        )

    # 2. Check for API Key
    if not TRANSLATOR_API_KEY:
        logging.error("TRANSLATOR_API_KEY is not set.")
        return func.HttpResponse(
            "Server configuration error: Translator API key is missing.",
            status_code=500
        )

    # 3. Prepare request for Translator API
    headers = {
        'Ocp-Apim-Subscription-Key': TRANSLATOR_API_KEY,
        'Ocp-Apim-Subscription-Region': 'japaneast',
        'Content-type': 'application/json'
    }
    params = {
        'api-version': '3.0',
        'from': 'ja',
        'to': 'en'
    }
    body = [{'text': text_to_translate}]
    
    # 4. Call API and return response
    try:
        response = requests.post(TRANSLATOR_ENDPOINT + '/translate', params=params, headers=headers, json=body)
        response.raise_for_status()
        
        translation_result = response.json()
        translated_text = translation_result[0]['translations'][0]['text']
        
        logging.info(f"Successfully translated.")
        return func.HttpResponse(translated_text)

    except requests.exceptions.RequestException as e:
        logging.error(f"Translator API request failed: {e}")
        return func.HttpResponse("Error calling translation service.", status_code=500)
    except (KeyError, IndexError) as e:
        logging.error(f"Failed to parse Translator API response: {e}")
        return func.HttpResponse("Error parsing translation response.", status_code=500)

import azure.functions as func
import logging
import os
import json
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text import TextTranslationClient

app = func.FunctionApp()

# 1. 環境変数の読み込み
KEY = os.environ.get("TRANSLATOR_KEY")
ENDPOINT = os.environ.get("TRANSLATOR_ENDPOINT")
REGION = os.environ.get("TRANSLATOR_REGION")

# 2. クライアントの初期化
def get_client():
    credential = AzureKeyCredential(KEY)
    return TextTranslationClient(endpoint=ENDPOINT, credential=credential, region=REGION)

@app.route(route="translate", auth_level=func.AuthLevel.ANONYMOUS)
def translate_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        body = req.get_json()
        text_to_translate = body.get('text')
    except Exception:
        return func.HttpResponse("Invalid JSON body.", status_code=400)

    if not text_to_translate:
        return func.HttpResponse("Please pass 'text' in the request body.", status_code=400)

    try:
        client = get_client()
        
        # [FINAL FIX] 最新のエラーメッセージに基づき引数を修正
        # body引数とto_language引数を両方指定する
        request_body = [{'Text': text_to_translate}]
        response = client.translate(body=request_body, to_language=["en"], from_language="ja")
        
        translated_text = response[0].translations[0].text
        
        return func.HttpResponse(
            json.dumps({"translated_text": translated_text}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Translation Error: {str(e)}")
        # 万が一、まだキーが破損している場合に備える
        if "Access denied" in str(e) or "Authentication" in str(e):
            return func.HttpResponse(f"Authentication Error: The Translator API key is likely invalid or expired. Please check your Azure configuration.", status_code=401)
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)

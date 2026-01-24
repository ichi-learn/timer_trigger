import azure.functions as func
import logging
import os
import json
import datetime
import time
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text import TextTranslationClient
from azure.data.tables import TableClient
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# 1. 環境変数の読み込み
VAULT_URL = os.environ.get("VAULT_URL")
TRANSLATOR_ENDPOINT = os.environ.get("TRANSLATOR_ENDPOINT")
TRANSLATOR_REGION = os.environ.get("TRANSLATOR_REGION")
STORAGE_CONNECTION_STRING = os.environ.get("AzureWebJobsStorage")

# 2. 定数
TABLE_NAME = "TranslationHistory"
PARTITION_KEY = "ja-en"

# 3. クライアントの初期化
def get_translation_client():
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=VAULT_URL, credential=credential)
    translator_key = secret_client.get_secret("TRANSLATOR-API-KEY").value
    return TextTranslationClient(endpoint=TRANSLATOR_ENDPOINT, credential=AzureKeyCredential(translator_key), region=TRANSLATOR_REGION)

def get_table_client():
    return TableClient.from_connection_string(conn_str=STORAGE_CONNECTION_STRING, table_name=TABLE_NAME)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        body = req.get_json()
        text_to_translate = body.get('text')
    except Exception:
        return func.HttpResponse("Invalid JSON body.", status_code=400)

    if not text_to_translate:
        return func.HttpResponse("Please pass 'text' in the request body.", status_code=400)

    try:
        # 翻訳の実行
        translation_client = get_translation_client()
        request_body = [{'Text': text_to_translate}]
        response = translation_client.translate(body=request_body, to_language=["en"], from_language="ja")
        translated_text = response[0].translations[0].text

        # --- 翻訳履歴の保存 --- 
        try:
            table_client = get_table_client()
            
            # Table Storageがなければ作成
            table_client.create_table_if_not_exists()

            timestamp = datetime.datetime.utcnow()
            entity = {
                'PartitionKey': PARTITION_KEY,
                'RowKey': str(time.time() * 1000000), # よりユニークな値にするためマイクロ秒単位に
                'OriginalText': text_to_translate,
                'TranslatedText': translated_text,
                'Timestamp': timestamp
            }
            table_client.create_entity(entity=entity)
            logging.info("Successfully saved translation history to table storage.")

        except Exception as e:
            # テーブル保存のエラーはログに記録するのみで、APIの応答には影響させない
            logging.error(f"Failed to save to Table Storage: {str(e)}")
        # ------------------------

        return func.HttpResponse(
            json.dumps({"translated_text": translated_text}, ensure_ascii=False),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(f"Translation Error: {str(e)}")
        if "Access denied" in str(e) or "Authentication" in str(e):
            return func.HttpResponse(f"Authentication Error: The Translator API key is likely invalid or expired. Please check your Azure configuration.", status_code=401)
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)

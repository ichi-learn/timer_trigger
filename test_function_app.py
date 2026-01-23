import unittest
from unittest.mock import patch, MagicMock, call
import json
import azure.functions as func
import function_app
import os

class TestFunctionApp(unittest.TestCase):

    # 環境変数をモックするための設定
    def setUp(self):
        self.mock_env = patch.dict(os.environ, {
            "TRANSLATOR_KEY": "fake_key",
            "TRANSLATOR_ENDPOINT": "https://fake.endpoint.com",
            "TRANSLATOR_REGION": "fakeregion",
            "AzureWebJobsStorage": "DefaultEndpointsProtocol=https;AccountName=fakeaccount;AccountKey=fakekey;EndpointSuffix=core.windows.net"
        })
        self.mock_env.start()

    def tearDown(self):
        self.mock_env.stop()

    @patch('function_app.get_table_client')
    @patch('function_app.get_translation_client')
    def test_translate_function_success_and_saves_history(self, mock_get_translation_client, mock_get_table_client):
        """正常な翻訳リクエストで、履歴が保存されることをテストする"""
        # --- 翻訳クライアントのモック設定 ---
        mock_translation_response = [{'translations': [{'text': 'Hello, world!'}]}]
        mock_translation_instance = MagicMock()
        mock_translation_instance.translate.return_value = mock_translation_response
        mock_get_translation_client.return_value = mock_translation_instance

        # --- テーブルクライアントのモック設定 ---
        mock_table_instance = MagicMock()
        mock_get_table_client.return_value = mock_table_instance

        # --- HTTPリクエストの作成 ---
        original_text = 'こんにちは、世界！'
        request_body = {'text': original_text}
        req = func.HttpRequest(
            method='POST',
            body=json.dumps(request_body, ensure_ascii=False).encode('utf-8'),
            url='/api/translate',
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )

        # --- 関数を実行 ---
        resp = function_app.translate_function(req)

        # --- 応答の検証 ---
        self.assertEqual(resp.status_code, 200)
        response_json = json.loads(resp.get_body().decode('utf-8'))
        self.assertEqual(response_json, {"translated_text": "Hello, world!"})

        # --- SDK呼び出しの検証 ---
        # 1. 翻訳APIが正しく呼ばれたか
        mock_translation_instance.translate.assert_called_once()
        
        # 2. Table Storageのテーブル作成処理が呼ばれたか
        mock_table_instance.create_table_if_not_exists.assert_called_once()

        # 3. Table Storageのエンティティ作成処理が呼ばれたか
        mock_table_instance.create_entity.assert_called_once()
        
        # 4. create_entityに渡されたエンティティの内容を検証
        args, kwargs = mock_table_instance.create_entity.call_args
        saved_entity = kwargs['entity']
        self.assertEqual(saved_entity['OriginalText'], original_text)
        self.assertEqual(saved_entity['TranslatedText'], 'Hello, world!')
        self.assertEqual(saved_entity['PartitionKey'], function_app.PARTITION_KEY)

    def test_translate_function_missing_text(self):
        """'text'フィールドが欠落しているリクエストをテストする"""
        req = func.HttpRequest(
            method='POST',
            body=json.dumps({}).encode('utf-8'),
            url='/api/translate',
            headers={'Content-Type': 'application/json'}
        )
        resp = function_app.translate_function(req)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Please pass 'text' in the request body.", resp.get_body().decode('utf-8'))

    @patch('function_app.get_translation_client')
    def test_translate_function_api_error(self, mock_get_translation_client):
        """翻訳APIでエラーが発生した場合をテストする"""
        mock_translation_instance = MagicMock()
        mock_translation_instance.translate.side_effect = Exception("API Call Failed")
        mock_get_translation_client.return_value = mock_translation_instance

        req = func.HttpRequest(
            method='POST',
            body=json.dumps({'text': 'error text'}).encode('utf-8'),
            url='/api/translate'
        )

        resp = function_app.translate_function(req)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("Error: API Call Failed", resp.get_body().decode('utf-8'))

if __name__ == '__main__':
    unittest.main()

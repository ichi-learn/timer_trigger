import unittest
from unittest.mock import MagicMock, patch, ANY
import json
import azure.functions as func
import function_app
import datetime

class TestTranslateFunction(unittest.TestCase):

    @patch.dict(function_app.os.environ, {
        "TRANSLATOR_KEY": "test-key",
        "TRANSLATOR_ENDPOINT": "https://api.cognitive.microsofttranslator.com/",
        "TRANSLATOR_REGION": "test-region",
        "AzureWebJobsStorage": "test-storage-connection-string"
    })
    def setUp(self):
        # This is a bit of a hack to reload the module with the patched environment variables
        # In a real application, you might use a more sophisticated way to manage configuration
        import importlib
        importlib.reload(function_app)


    @patch('function_app.get_table_client')
    @patch('function_app.get_translation_client')
    def test_translate_function_success_and_saves_history(self, mock_get_translation_client, mock_get_table_client):
        """正常な翻訳リクエストで、履歴が保存されることをテストする"""
        # --- 翻訳クライアントのモック設定 (修正) ---
        # 実際のAPI応答に近いオブジェクト構造をモックで作成
        mock_translated_text_obj = MagicMock()
        mock_translated_text_obj.text = 'Hello, world!'

        mock_translation_item = MagicMock()
        mock_translation_item.translations = [mock_translated_text_obj]

        mock_translation_response = [mock_translation_item]
        # --- ここまで修正 ---

        mock_translation_instance = MagicMock()
        mock_translation_instance.translate.return_value = mock_translation_response
        mock_get_translation_client.return_value = mock_translation_instance

        # --- テーブルクライアントのモック設定 ---
        mock_table_instance = MagicMock()
        mock_get_table_client.return_value = mock_table_instance

        # --- リクエストの準備 ---
        req = func.HttpRequest(
            method='POST',
            body=json.dumps({'text': 'こんにちは、世界！'}).encode('utf-8'),
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

        # 4. create_entity に渡されたパラメータの内容を検証
        called_entity = mock_table_instance.create_entity.call_args.kwargs['entity']
        self.assertEqual(called_entity['PartitionKey'], 'ja-en')
        self.assertEqual(called_entity['OriginalText'], 'こんにちは、世界！')
        self.assertEqual(called_entity['TranslatedText'], 'Hello, world!')
        self.assertIn('RowKey', called_entity)
        self.assertTrue(isinstance(called_entity['RowKey'], str))
        self.assertIn('Timestamp', called_entity)
        self.assertTrue(isinstance(called_entity['Timestamp'], datetime.datetime))


    @patch('function_app.get_table_client')
    @patch('function_app.get_translation_client')
    def test_translate_function_table_storage_error(self, mock_get_translation_client, mock_get_table_client):
        """テーブルストレージへの保存に失敗しても、翻訳結果は正常に返されることをテストする"""
        # --- 翻訳クライアントのモック設定 ---
        mock_translated_text_obj = MagicMock()
        mock_translated_text_obj.text = 'Hello'
        mock_translation_item = MagicMock()
        mock_translation_item.translations = [mock_translated_text_obj]
        mock_translation_response = [mock_translation_item]

        mock_translation_instance = MagicMock()
        mock_translation_instance.translate.return_value = mock_translation_response
        mock_get_translation_client.return_value = mock_translation_instance

        # --- テーブルクライアントのモック設定 (エラーを発生させる) ---
        mock_table_instance = MagicMock()
        mock_table_instance.create_entity.side_effect = Exception("Table storage error")
        mock_get_table_client.return_value = mock_table_instance
        
        # --- リクエストの準備 ---
        req = func.HttpRequest(
            method='POST',
            body=json.dumps({'text': 'こんにちは'}).encode('utf-8'),
            url='/api/translate',
             headers={'Content-Type': 'application/json; charset=utf-8'}
        )

        # --- 関数を実行 ---
        resp = function_app.translate_function(req)

        # --- 応答の検証 ---
        # テーブルストレージのエラーに関わらず、ステータスコード200が返されるはず
        self.assertEqual(resp.status_code, 200)
        response_json = json.loads(resp.get_body().decode('utf-8'))
        self.assertEqual(response_json, {"translated_text": "Hello"})
        
        # --- SDK呼び出しの検証 ---
        mock_table_instance.create_table_if_not_exists.assert_called_once()
        mock_table_instance.create_entity.assert_called_once()


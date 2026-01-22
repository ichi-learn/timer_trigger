
import unittest
from unittest.mock import patch, MagicMock
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
            "TRANSLATOR_REGION": "fakeregion"
        })
        self.mock_env.start()

    def tearDown(self):
        self.mock_env.stop()

    @patch('function_app.TextTranslationClient')
    def test_translate_function_success(self, mock_translation_client):
        """正常な翻訳リクエストをテストする"""
        # モックの設定：SDKが返す偽の翻訳結果
        mock_response = [{'translations': [{'text': 'Hello, world!'}]}]
        mock_instance = MagicMock()
        mock_instance.translate.return_value = mock_response
        mock_translation_client.return_value = mock_instance

        request_body = {'text': 'こんにちは、世界！'}
        req = func.HttpRequest(
            method='POST',
            body=json.dumps(request_body, ensure_ascii=False).encode('utf-8'),
            url='/api/translate_function',
            headers={'Content-Type': 'application/json; charset=utf-8'}
        )

        # 関数を実行
        resp = function_app.translate_function(req)
        self.assertEqual(resp.status_code, 200)

        # 結果を検証
        response_json = json.loads(resp.get_body().decode('utf-8'))
        self.assertEqual(response_json, {"translated_text": "Hello, world!"})

        # SDKのtranslateメソッドが正しい引数で呼び出されたか検証
        mock_instance.translate.assert_called_once_with(content=['こんにちは、世界！'], to_language="en", from_language="ja")

    def test_translate_function_missing_text(self):
        """textフィールドが欠落しているリクエストをテストする"""
        req = func.HttpRequest(
            method='POST',
            body=json.dumps({}).encode('utf-8'),
            url='/api/translate_function',
            headers={'Content-Type': 'application/json'}
        )
        resp = function_app.translate_function(req)
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b"Please pass a 'text' field in the request body.", resp.get_body())

    @patch('function_app.TextTranslationClient')
    def test_translate_function_api_error(self, mock_translation_client):
        """翻訳APIでエラーが発生した場合をテストする"""
        # モックの設定：SDKが例外を発生させる
        mock_instance = MagicMock()
        mock_instance.translate.side_effect = Exception("API Call Failed")
        mock_translation_client.return_value = mock_instance

        request_body = {'text': 'エラーを発生させるテキスト'}
        req = func.HttpRequest(
            method='POST',
            body=json.dumps(request_body, ensure_ascii=False).encode('utf-8'),
            url='/api/translate_function',
            headers={'Content-Type': 'application/json'}
        )

        # 関数を実行
        resp = function_app.translate_function(req)

        # 結果を検証：サーバーエラー(500)が返されること
        self.assertEqual(resp.status_code, 500)
        self.assertIn(b"Sorry, something went wrong during translation.", resp.get_body())

if __name__ == '__main__':
    unittest.main()

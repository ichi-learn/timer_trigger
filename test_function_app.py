
import unittest
from unittest.mock import patch, Mock
import azure.functions as func
import function_app  # Assuming the file is named function_app.py

class TestFunctionApp(unittest.TestCase):

    @patch('function_app.perform_translation')
    def test_translate_function_success(self, mock_perform_translation):
        """
        Test the translate_function for a successful translation.
        """
        # Arrange
        mock_perform_translation.return_value = "Hello"
        req = func.HttpRequest(
            method='GET',
            body=None,
            url='/api/translate',
            params={'text': 'こんにちは'}
        )

        # Act
        resp = function_app.translate_function.get_user_function()(req)

        # Assert
        self.assertEqual(resp.get_body(), b'Hello')
        self.assertEqual(resp.status_code, 200)

    def test_translate_function_missing_text(self):
        """
        Test the translate_function when the 'text' parameter is missing.
        """
        # Arrange
        req = func.HttpRequest(
            method='GET',
            body=None,
            url='/api/translate',
            params={}
        )

        # Act
        resp = function_app.translate_function.get_user_function()(req)

        # Assert
        self.assertIn(b"Please pass a 'text'", resp.get_body())
        self.assertEqual(resp.status_code, 400)

    @patch('function_app.logging')
    def test_daily_notifier(self, mock_logging):
        """
        Test the daily_notifier to ensure it logs the correct messages.
        """
        # Arrange
        timer_req = func.TimerRequest(
            past_due=False,
            schedule_status=None,
            schedule=None,
            is_past_due=False,
            schedule_status_next=None
        )

        # Act
        function_app.daily_notifier.get_user_function()(timer_req)

        # Assert
        # Check if logging.info was called with the expected messages
        mock_logging.info.assert_any_call('Scheduled task started')
        mock_logging.info.assert_any_call("Simulating translation for: 'こんにちは'. In a real scenario, this would be translated.")
        mock_logging.info.assert_any_call('Python timer trigger function executed.')

if __name__ == '__main__':
    unittest.main()

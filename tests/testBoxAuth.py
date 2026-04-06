import unittest

from unittest.mock import patch, MagicMock, mock_open
from queue import Queue
from box import box_auth


class TestOAuthCallbackHandler(unittest.TestCase):
    def setUp(self):
        self.queue = Queue()
        self.server = MagicMock()
        self.server.queue = self.queue
        self.handler = box_auth.OAuthCallbackHandler
        self.handler.server = self.server

    @patch("box.box_auth.OAuthCallbackHandler.send_response")
    @patch("box.box_auth.OAuthCallbackHandler.send_header")
    @patch("box.box_auth.OAuthCallbackHandler.end_headers")
    def test_do_GET_with_code_file_found(
        self, mock_end_headers, mock_send_header, mock_send_response
    ):
        handler = self.handler
        handler.path = "/?code=abc123"
        handler.server = self.server
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        # Simulate file found
        fake_html = b"<html>Success file</html>"
        m = mock_open(read_data=fake_html)
        with patch("builtins.open", m):
            with patch("threading.Thread") as mock_thread:
                handler.do_GET(handler)
                self.assertEqual(self.queue.get(), "abc123")
                handler.send_response.assert_called_with(200)
                handler.send_header.assert_called_with("Content-type", "text/html")
                handler.end_headers.assert_called()
                handler.wfile.write.assert_called_with(fake_html)
                mock_thread.assert_called()

    @patch("box.box_auth.OAuthCallbackHandler.send_response")
    @patch("box.box_auth.OAuthCallbackHandler.send_header")
    @patch("box.box_auth.OAuthCallbackHandler.end_headers")
    def test_do_GET_with_code_file_not_found(
        self, mock_end_headers, mock_send_header, mock_send_response
    ):
        handler = self.handler
        handler.path = "/?code=abc123"
        handler.server = self.server
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        # Simulate file not found
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("threading.Thread") as mock_thread:
                handler.do_GET(handler)
                self.assertEqual(self.queue.get(), "abc123")
                handler.send_response.assert_called_with(200)
                handler.send_header.assert_called_with("Content-type", "text/html")
                handler.end_headers.assert_called()
                handler.wfile.write.assert_called_with(
                    b"<html><body><h2>Authentication successful!</h2>"
                    b"You can close this window.</body></html>"
                )
                mock_thread.assert_called()

    @patch("box.box_auth.OAuthCallbackHandler.send_error")
    def test_do_GET_missing_code(self, mock_send_error):
        handler = self.handler
        handler.path = "/?notcode="
        handler.server = self.server
        handler.send_error = MagicMock()
        handler.do_GET(handler)
        handler.send_error.assert_called_with(400, "Missing 'code' parameter in query")


class TestThreadedHTTPServer(unittest.TestCase):
    def test_queue_attached(self):
        queue = Queue()
        server = box_auth.ThreadedHTTPServer(
            ("localhost", 8000), box_auth.OAuthCallbackHandler, queue
        )
        self.assertIs(server.queue, queue)

        server.server_close()


class TestGetAuthorizationCode(unittest.TestCase):
    @patch("box.box_auth.webbrowser.open")
    @patch("box.box_auth.ThreadedHTTPServer")
    def test_get_authorization_code_success(self, mock_server_class, mock_webbrowser_open):
        queue = Queue()
        queue.put("test_code")
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        dummy_settings = MagicMock()
        dummy_settings.REDIRECT_HOST = "localhost"
        dummy_settings.REDIRECT_PORT = 8000

        with patch("box.box_auth.get_box_settings", return_value=dummy_settings):
            code = box_auth.get_authorization_code("http://auth.url", queue)
            self.assertEqual(code, "test_code")
            mock_webbrowser_open.assert_called_once()

    @patch("box.box_auth.webbrowser.open")
    @patch("box.box_auth.ThreadedHTTPServer")
    def test_get_authorization_code_timeout(self, mock_server_class, mock_webbrowser_open):
        queue = Queue()
        mock_server = MagicMock()
        mock_server_class.return_value = mock_server

        dummy_settings = MagicMock()
        dummy_settings.REDIRECT_HOST = "localhost"
        dummy_settings.REDIRECT_PORT = 8000

        with patch("box.box_auth.get_box_settings", return_value=dummy_settings):
            mock_webbrowser_open.assert_not_called()
            with self.assertRaises(TimeoutError):
                box_auth.get_authorization_code("http://auth.url", queue, timeout=0.01)


class TestAuthenticateOAuth(unittest.TestCase):
    @patch("box.box_auth.load_tokens", return_value=(None, None))
    @patch("box.box_auth.OAuth2")
    @patch("box.box_auth.get_authorization_code", return_value="auth_code")
    @patch("box.box_auth.Client")
    def test_authenticate_oauth_no_tokens(
        self, mock_client, mock_get_code, mock_oauth2_class, mock_load_tokens
    ):
        settings = MagicMock()
        settings.BOX_CLIENT_ID = "id"
        settings.BOX_CLIENT_SECRET = "secret"
        settings.REDIRECT_HOST = "localhost"
        settings.REDIRECT_PORT = 8000

        mock_oauth2 = MagicMock()
        mock_oauth2.get_authorization_url.return_value = ("http://auth.url", "csrf")
        mock_oauth2.authenticate = MagicMock()
        mock_oauth2_class.return_value = mock_oauth2

        box_auth.authenticate_oauth(settings)
        mock_oauth2.get_authorization_url.assert_called_once()
        mock_get_code.assert_called_once()
        mock_oauth2.authenticate.assert_called_once_with("auth_code")
        mock_client.assert_called_once_with(mock_oauth2)

    @patch("box.box_auth.load_tokens", return_value=("access", "refresh"))
    @patch("box.box_auth.OAuth2")
    @patch("box.box_auth.Client")
    def test_authenticate_oauth_with_tokens(self, mock_client, mock_oauth2_class, mock_load_tokens):
        settings = MagicMock()
        settings.BOX_CLIENT_ID = "id"
        settings.BOX_CLIENT_SECRET = "secret"
        settings.REDIRECT_HOST = "localhost"
        settings.REDIRECT_PORT = 8000

        mock_oauth2 = MagicMock()
        mock_oauth2_class.return_value = mock_oauth2

        box_auth.authenticate_oauth(settings)
        mock_oauth2_class.assert_called_once()
        mock_client.assert_called_once_with(mock_oauth2)


if __name__ == "__main__":
    unittest.main()

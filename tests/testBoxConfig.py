import unittest

from unittest.mock import patch, mock_open
from box import box_config


class testBoxConfig(unittest.TestCase):
    def setUp(self):
        self.boxSettings = box_config.BoxSettings(
            BOX_CLIENT_ID="abc123",
            BOX_CLIENT_SECRET="supersecret",
            REDIRECT_HOST="localhost",
            REDIRECT_PORT=80,
            TOKEN_STORE="token",
            FOLDER=1234,
        )

        self.boxSettings_patcher = patch("box.box_config.get_box_settings").start()

        self.boxSettings_patcher.return_value = self.boxSettings

    def tearDown(self):
        self.boxSettings_patcher.stop()

    def test_box_settings(self):
        self.assertIsInstance(self.boxSettings, box_config.BaseSettings)
        self.assertEqual("box", self.boxSettings.base_path.name)

    def test_get_box_settings(self):
        settings = box_config.get_box_settings()

        self.assertIsInstance(settings, box_config.BaseSettings)
        self.assertEqual(settings, self.boxSettings)

    @patch("builtins.open", new_callable=mock_open())
    @patch("json.dump")
    @patch("builtins.print")
    def test_store_tokens(self, mock_print, mock_json_dump, mock_file):
        mock_access_token = "abc123"
        mock_refresh_token = "xyz321"

        box_config.store_tokens_callback(
            access_token=mock_access_token, refresh_token=mock_refresh_token
        )

        token_path = f"{self.boxSettings.base_path}/{self.boxSettings.TOKEN_STORE}"

        mock_file.assert_called_once_with(token_path, "w")
        mock_json_dump.assert_called_once_with(
            {"access_token": mock_access_token, "refresh_token": mock_refresh_token},
            mock_file().__enter__(),
        )
        mock_print.assert_called()

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="{}")
    @patch("json.load", return_value={"access_token": "A", "refresh_token": "R"})
    def test_load_tokens_exist(self, mock_json_load, mock_file, mock_exists):
        access, refresh = box_config.load_tokens()
        token_path = f"{self.boxSettings.base_path}/{self.boxSettings.TOKEN_STORE}"

        mock_file.assert_called_once_with(token_path, "r")
        mock_json_load.assert_called_once()
        self.assertEqual((access, refresh), ("A", "R"))

    @patch("os.path.exists", return_value=False)
    def test_load_tokens_not_exist(self, mock_exists):
        access, refresh = box_config.load_tokens()
        self.assertEqual((access, refresh), (None, None))

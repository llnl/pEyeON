from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path
import json
import os


class BoxSettings(BaseSettings):
    BOX_CLIENT_ID: str
    BOX_CLIENT_SECRET: str
    REDIRECT_HOST: str
    REDIRECT_PORT: int
    TOKEN_STORE: str
    FOLDER: int

    model_config = SettingsConfigDict(env_file=f"{Path(__file__).parent}/box.env")

    @property
    def base_path(self):
        """
        helps allow the box command to be run from different directories
        """
        return Path(__file__).parent


@lru_cache(maxsize=1)
def get_box_settings():
    return BoxSettings()


# ─── TOKEN PERSISTENCE ─────────────────────────────────────────────────────────
def store_tokens_callback(access_token: str, refresh_token: str) -> None:
    """
    callback for use with boxsdk OAuth2
    """
    box_config = get_box_settings()
    token_path = f"{box_config.base_path}/{box_config.TOKEN_STORE}"

    with open(token_path, "w") as f:
        json.dump({"access_token": access_token, "refresh_token": refresh_token}, f)

    print(f"tokens saved successfully: {token_path}")


def load_tokens():
    box_config = get_box_settings()
    token_path = f"{box_config.base_path}/{box_config.TOKEN_STORE}"

    if os.path.exists(token_path):
        with open(token_path, "r") as f:
            data = json.load(f)
            return data.get("access_token"), data.get("refresh_token")
    return None, None

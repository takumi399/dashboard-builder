"""Encryption helpers for persisted data-source connection configuration."""

import json

from cryptography.fernet import Fernet, InvalidToken

ENCRYPTED_PREFIX = "fernet:v1:"


class CredentialCipher:
    """Encrypt connection configuration while supporting legacy JSON values."""

    def __init__(self, key: str):
        try:
            self._fernet = Fernet(key.encode())
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(
                "DATASOURCE_ENCRYPTION_KEY must be a valid Fernet key"
            ) from exc

    def encrypt(self, config: dict) -> str:
        payload = json.dumps(
            config, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return ENCRYPTED_PREFIX + self._fernet.encrypt(payload).decode("ascii")

    def decrypt(self, stored: str) -> dict:
        try:
            if stored.startswith(ENCRYPTED_PREFIX):
                token = stored.removeprefix(ENCRYPTED_PREFIX).encode("ascii")
                payload = self._fernet.decrypt(token).decode("utf-8")
            else:
                payload = stored
            result = json.loads(payload)
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            raise ValueError("Stored data-source credentials are invalid") from exc

        if not isinstance(result, dict):
            raise ValueError("Stored data-source credentials must be an object")
        return result

    @staticmethod
    def public_config(config: dict) -> dict:
        return {key: value for key, value in config.items() if key != "password"}

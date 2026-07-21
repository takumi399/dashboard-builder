import json

import pytest
from cryptography.fernet import Fernet

from app.services.credential_cipher import CredentialCipher, ENCRYPTED_PREFIX


def test_cipher_encrypts_password_and_round_trips():
    cipher = CredentialCipher(Fernet.generate_key().decode())
    config = {
        "db_type": "postgresql",
        "host": "db.example.com",
        "port": 5432,
        "database": "analytics",
        "username": "reader",
        "password": "top-secret",
    }

    stored = cipher.encrypt(config)

    assert stored.startswith(ENCRYPTED_PREFIX)
    assert "top-secret" not in stored
    assert cipher.decrypt(stored) == config


def test_cipher_reads_legacy_plaintext_json():
    cipher = CredentialCipher(Fernet.generate_key().decode())
    legacy = json.dumps({"db_type": "sqlite", "database": "sample.db"})
    assert cipher.decrypt(legacy)["database"] == "sample.db"


def test_cipher_rejects_invalid_key():
    with pytest.raises(ValueError, match="DATASOURCE_ENCRYPTION_KEY"):
        CredentialCipher("not-a-fernet-key")


def test_public_config_removes_password():
    config = {"db_type": "sqlite", "database": "sample.db", "password": "secret"}
    assert CredentialCipher.public_config(config) == {
        "db_type": "sqlite",
        "database": "sample.db",
    }

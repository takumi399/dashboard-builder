import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_datasource_encryption_key():
    with pytest.raises(ValidationError, match="DATASOURCE_ENCRYPTION_KEY"):
        Settings(DEBUG=False, DATASOURCE_ENCRYPTION_KEY="")


def test_production_rejects_malformed_datasource_encryption_key():
    with pytest.raises(ValidationError, match="DATASOURCE_ENCRYPTION_KEY"):
        Settings(DEBUG=False, DATASOURCE_ENCRYPTION_KEY="not-a-fernet-key")

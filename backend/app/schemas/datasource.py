from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DataSourceCreate(BaseModel):
    name: str
    source_type: str
    raw_data: Optional[str] = None
    config_json: str = "{}"

class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    config_json: str
    raw_data: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChartCreate(BaseModel):
    chart_type: str
    title: str = "Untitled Chart"
    position_x: float = 0
    position_y: float = 0
    width: float = 400
    height: float = 300
    data_source_id: Optional[int] = None
    config_json: str = "{}"
    query_config: str = "{}"
    sort_order: int = 0

class ChartUpdate(BaseModel):
    title: Optional[str] = None
    chart_type: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    config_json: Optional[str] = None
    data_source_id: Optional[int] = None
    query_config: Optional[str] = None
    sort_order: Optional[int] = None

class ChartResponse(BaseModel):
    id: int
    dashboard_id: int
    chart_type: str
    title: str
    position_x: float
    position_y: float
    width: float
    height: float
    data_source_id: Optional[int]
    config_json: str
    query_config: str
    sort_order: int

    model_config = {"from_attributes": True}

class DashboardCreate(BaseModel):
    name: str
    description: str = ""

class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class DashboardResponse(BaseModel):
    id: int
    name: str
    description: str
    is_published: bool
    share_token: Optional[str]
    created_at: datetime
    updated_at: datetime
    charts: List[ChartResponse] = []

    model_config = {"from_attributes": True}

class DashboardListResponse(BaseModel):
    id: int
    name: str
    description: str
    is_published: bool
    created_at: datetime
    updated_at: datetime
    chart_count: int = 0

    model_config = {"from_attributes": True}

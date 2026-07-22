from pydantic import BaseModel, field_validator, model_validator
from typing import Literal, Optional, List
from datetime import datetime

from app.core.security import contains_html


ChartType = Literal['bar', 'line', 'pie', 'scatter', 'heatmap', 'radar', 'funnel', 'card', 'table']


class ChartCreate(BaseModel):
    chart_type: ChartType
    title: str = "Untitled Chart"

    @field_validator('title')
    @classmethod
    def validate_title_no_xss(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError('图表标题不能超过 100 个字符')
        if contains_html(v):
            raise ValueError('图表标题不能包含 HTML 标签')
        return v
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
    chart_type: Optional[ChartType] = None
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
    chart_type: ChartType
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

    @model_validator(mode='after')
    def validate_name_no_xss(self):
        v = self.name
        if len(v) > 100:
            raise ValueError('看板名称不能超过 100 个字符')
        if contains_html(v):
            raise ValueError('看板名称不能包含 HTML 标签')
        return self

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
    role: Optional[str] = None  # 当前用户在此看板中的角色

    model_config = {"from_attributes": True}

class MemberCreate(BaseModel):
    user_id: int
    role: str  # "editor" | "viewer"

class MemberResponse(BaseModel):
    id: int
    user_id: int
    role: str
    username: str
    created_at: datetime

    model_config = {"from_attributes": True}

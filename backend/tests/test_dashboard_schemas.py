import pytest
from pydantic import ValidationError

from app.schemas.dashboard import ChartCreate, ChartResponse, ChartUpdate


@pytest.mark.parametrize(
    ("schema", "payload"),
    [
        (ChartCreate, {"chart_type": "unsupported"}),
        (ChartUpdate, {"chart_type": "unsupported"}),
        (
            ChartResponse,
            {
                "id": 1,
                "dashboard_id": 1,
                "chart_type": "unsupported",
                "title": "Invalid chart",
                "position_x": 0,
                "position_y": 0,
                "width": 400,
                "height": 300,
                "data_source_id": None,
                "config_json": "{}",
                "query_config": "{}",
                "sort_order": 0,
            },
        ),
    ],
)
def test_chart_schemas_reject_unsupported_chart_types(schema, payload):
    with pytest.raises(ValidationError):
        schema.model_validate(payload)

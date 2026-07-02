import json, csv, io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.dashboard import DataSource
from app.schemas.datasource import DataSourceCreate, DataSourceResponse

router = APIRouter()

@router.get("", response_model=list[DataSourceResponse])
async def list_datasources(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.user_id == current_user.id).order_by(DataSource.created_at.desc()))
    return [DataSourceResponse.model_validate(ds) for ds in result.scalars().all()]

@router.post("/upload", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv(name: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db), file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    content = await file.read()
    text = content.decode('utf-8')
    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader]
    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    ds = DataSource(user_id=current_user.id, name=name, source_type="csv", raw_data=json.dumps(rows), config_json=json.dumps({"filename": file.filename, "columns": list(rows[0].keys()), "row_count": len(rows)}))
    db.add(ds)
    await db.commit()
    await db.refresh(ds)
    return DataSourceResponse.model_validate(ds)

@router.get("/{datasource_id}/data")
async def get_datasource_data(datasource_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.id == datasource_id, DataSource.user_id == current_user.id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    return {"id": ds.id, "name": ds.name, "columns": json.loads(ds.config_json).get("columns", []), "rows": json.loads(ds.raw_data or "[]"), "row_count": json.loads(ds.config_json).get("row_count", 0)}

@router.delete("/{datasource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(datasource_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DataSource).where(DataSource.id == datasource_id, DataSource.user_id == current_user.id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Data source not found")
    await db.delete(ds)
    await db.commit()

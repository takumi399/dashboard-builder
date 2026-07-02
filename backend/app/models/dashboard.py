from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Dashboard(Base):
    __tablename__ = "dashboards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    is_published = Column(Boolean, default=False)
    share_token = Column(String(64), unique=True, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", backref="dashboards")
    charts = relationship("Chart", back_populates="dashboard", cascade="all, delete-orphan")

class Chart(Base):
    __tablename__ = "charts"

    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False)
    chart_type = Column(String(20), nullable=False)
    title = Column(String(100), default="Untitled Chart")
    config_json = Column(Text, default="{}")
    position_x = Column(Float, default=0)
    position_y = Column(Float, default=0)
    width = Column(Float, default=400)
    height = Column(Float, default=300)
    data_source_id = Column(Integer, ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True)
    query_config = Column(Text, default="{}")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    dashboard = relationship("Dashboard", back_populates="charts")
    data_source = relationship("DataSource", backref="charts")

class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    source_type = Column(String(20), nullable=False)
    config_json = Column(Text, default="{}")
    raw_data = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User", backref="data_sources")

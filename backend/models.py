from sqlalchemy import Column, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from database import Base


class UserRole(str, enum.Enum):
    visitor = "visitor"
    operator = "operator"
    admin = "admin"
    integrator = "integrator"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.visitor)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Piece(Base):
    __tablename__ = "pieces"

    id = Column(Integer, primary_key=True, index=True)
    piece_code = Column(String, unique=True, index=True, nullable=False)  # e.g. "P001"
    piece_name = Column(String, nullable=False)
    material = Column(String, nullable=False)
    dimensions = Column(String, nullable=True)  # e.g. "180 X 120 X 20"
    adhesive_type = Column(String, nullable=True)
    estimated_glue_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class HistoryRecord(Base):
    __tablename__ = "history_records"

    id = Column(Integer, primary_key=True, index=True)
    piece_id = Column(Integer, ForeignKey("pieces.id"), nullable=False)
    run_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="completed")  # completed / failed, room to grow later

    piece = relationship("Piece", backref="history_records")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    robot_pc_url = Column(String, nullable=True)  # e.g. "http://192.168.1.50:8001"
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
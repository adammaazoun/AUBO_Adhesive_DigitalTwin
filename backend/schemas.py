from pydantic import BaseModel, EmailStr
from datetime import datetime
from models import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# What the client sends when creating a user (signup)
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.visitor


# What the API sends back — notice: NO password field, ever
class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True  # allows Pydantic to read directly from SQLAlchemy objects


class UserRoleUpdate(BaseModel):
    role: UserRole


class PieceCreate(BaseModel):
    piece_code: str
    piece_name: str
    material: str
    dimensions: str | None = None
    adhesive_type: str | None = None
    estimated_glue_time_seconds: int | None = None


class PieceUpdate(BaseModel):
    piece_name: str | None = None
    material: str | None = None
    dimensions: str | None = None
    adhesive_type: str | None = None
    estimated_glue_time_seconds: int | None = None


class PieceResponse(BaseModel):
    id: int
    piece_code: str
    piece_name: str
    material: str
    dimensions: str | None
    adhesive_type: str | None
    estimated_glue_time_seconds: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class HistoryCreate(BaseModel):
    piece_code: str  # client sends the human-readable code, we resolve it internally
    status: str = "completed"


class HistoryResponse(BaseModel):
    id: int
    run_date: datetime
    status: str
    piece: PieceResponse  # nested — this is what gives you "More Details" in one call

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    robot_pc_url: str


class SettingsResponse(BaseModel):
    id: int
    robot_pc_url: str | None
    updated_at: datetime

    class Config:
        from_attributes = True


class RobotCommand(BaseModel):
    command: str  # "start" | "pause" | "stop"
    piece_code: str | None = None  # needed for "start"


class RobotParameters(BaseModel):
    speed_fraction: float  # 0.02 - 2.0
    acc: float             # 0.05 - 3.0 m/s²
    blend_radius_mm: float  # 0 - 50 mm


class RobotCommandResponse(BaseModel):
    success: bool
    message: str
    robot_response: dict | None = None


class PieceImportResult(BaseModel):
    piece_code: str | None = None
    piece_name: str | None = None
    material: str | None = None
    dimensions: str | None = None
    adhesive_type: str | None = None
    estimated_glue_time_seconds: int | None = None
    raw_text: str  # full extracted text, so the user can manually check anything the parser missed
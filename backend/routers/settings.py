from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from auth import require_role
from models import UserRole

router = APIRouter(prefix="/settings", tags=["settings"])


def get_or_create_settings(db: Session) -> models.AppSettings:
    settings = db.query(models.AppSettings).first()
    if not settings:
        settings = models.AppSettings(robot_pc_url=None)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/", response_model=schemas.SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    return get_or_create_settings(db)


@router.put("/", response_model=schemas.SettingsResponse)
def update_settings(
    updates: schemas.SettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.admin)),
):
    settings = get_or_create_settings(db)
    settings.robot_pc_url = updates.robot_pc_url
    db.commit()
    db.refresh(settings)
    return settings
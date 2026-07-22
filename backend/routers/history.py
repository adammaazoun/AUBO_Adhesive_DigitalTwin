from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from database import get_db
import models
import schemas
from auth import require_role
from models import UserRole

router = APIRouter(prefix="/history", tags=["history"])


@router.post("/", response_model=schemas.HistoryResponse)
def create_history_record(
    record: schemas.HistoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    piece = db.query(models.Piece).filter(models.Piece.piece_code == record.piece_code).first()
    if not piece:
        raise HTTPException(status_code=404, detail="Piece not found")

    new_record = models.HistoryRecord(piece_id=piece.id, status=record.status)
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    return new_record


@router.get("/", response_model=list[schemas.HistoryResponse])
def list_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    return (
        db.query(models.HistoryRecord)
        .options(joinedload(models.HistoryRecord.piece))
        .order_by(models.HistoryRecord.run_date.desc())
        .all()
    )


@router.get("/{record_id}", response_model=schemas.HistoryResponse)
def get_history_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    record = (
        db.query(models.HistoryRecord)
        .options(joinedload(models.HistoryRecord.piece))
        .filter(models.HistoryRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="History record not found")
    return record
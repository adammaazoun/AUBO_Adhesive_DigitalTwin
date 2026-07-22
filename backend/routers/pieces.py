from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from auth import require_role
from models import UserRole

router = APIRouter(prefix="/pieces", tags=["pieces"])


@router.post("/", response_model=schemas.PieceResponse)
def create_piece(
    piece: schemas.PieceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.admin)),
):
    existing = db.query(models.Piece).filter(models.Piece.piece_code == piece.piece_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Piece code already exists")

    new_piece = models.Piece(**piece.model_dump())
    db.add(new_piece)
    db.commit()
    db.refresh(new_piece)
    return new_piece


@router.get("/", response_model=list[schemas.PieceResponse])
def list_pieces(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    return db.query(models.Piece).order_by(models.Piece.created_at.desc()).all()


@router.get("/{piece_code}", response_model=schemas.PieceResponse)
def get_piece(
    piece_code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    piece = db.query(models.Piece).filter(models.Piece.piece_code == piece_code).first()
    if not piece:
        raise HTTPException(status_code=404, detail="Piece not found")
    return piece


@router.put("/{piece_code}", response_model=schemas.PieceResponse)
def update_piece(
    piece_code: str,
    updates: schemas.PieceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.admin)),
):
    piece = db.query(models.Piece).filter(models.Piece.piece_code == piece_code).first()
    if not piece:
        raise HTTPException(status_code=404, detail="Piece not found")

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(piece, field, value)

    db.commit()
    db.refresh(piece)
    return piece


@router.delete("/{piece_code}")
def delete_piece(
    piece_code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.admin)),
):
    piece = db.query(models.Piece).filter(models.Piece.piece_code == piece_code).first()
    if not piece:
        raise HTTPException(status_code=404, detail="Piece not found")

    db.delete(piece)
    db.commit()
    return {"message": f"Piece {piece_code} deleted"}
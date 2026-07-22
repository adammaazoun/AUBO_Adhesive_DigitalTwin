import re
import io
import pdfplumber
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from auth import require_role
from models import UserRole

router = APIRouter(prefix="/pieces", tags=["pieces"])


def extract_field(text: str, patterns: list[str]) -> str | None:
    """Try each regex pattern in order, return the first match found."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


@router.post("/import-pdf", response_model=schemas.PieceImportResult)
async def import_piece_pdf(
    file: UploadFile = File(...),
    current_user: models.User = Depends(require_role(UserRole.admin)),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    contents = await file.read()

    try:
        with pdfplumber.open(io.BytesIO(contents)) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {str(e)}")

    if not full_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No extractable text found — this PDF may be a scanned image, which isn't supported yet",
        )

    piece_code = extract_field(full_text, [
        r"(?:piece\s*)?code[:\-]\s*(\S+)",
        r"\b(P\d{3,})\b",
    ])
    piece_name = extract_field(full_text, [
        r"(?:piece\s*)?name[:\-]\s*(.+)",
    ])
    material = extract_field(full_text, [
        r"material[:\-]\s*(.+)",
    ])
    dimensions = extract_field(full_text, [
        r"dimensions?[:\-]\s*(.+)",
        r"(\d+\s*[xX]\s*\d+\s*[xX]\s*\d+)",
    ])
    adhesive_type = extract_field(full_text, [
        r"adhesive(?:\s*type)?[:\-]\s*(.+)",
    ])
    glue_time_str = extract_field(full_text, [
        r"(?:estimated\s*)?glue\s*time[:\-]\s*(\d+)",
    ])

    return schemas.PieceImportResult(
        piece_code=piece_code,
        piece_name=piece_name,
        material=material,
        dimensions=dimensions,
        adhesive_type=adhesive_type,
        estimated_glue_time_seconds=int(glue_time_str) if glue_time_str else None,
        raw_text=full_text,
    )
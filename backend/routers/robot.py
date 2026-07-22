import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
import models
import schemas
from auth import require_role
from models import UserRole
from routers.settings import get_or_create_settings

router = APIRouter(prefix="/robot", tags=["robot"])


async def get_robot_pc_url(db: Session) -> str:
    settings = get_or_create_settings(db)
    if not settings.robot_pc_url:
        raise HTTPException(status_code=400, detail="Robot PC URL is not configured in Settings")
    return settings.robot_pc_url


@router.get("/status")
async def get_robot_status(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.visitor)),
):
    settings = get_or_create_settings(db)
    if not settings.robot_pc_url:
        return {"online": False, "pipeline_running": False, "reason": "Robot PC URL not configured"}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.robot_pc_url}/status")
            response.raise_for_status()
            data = response.json()
            return {"online": True, "pipeline_running": data.get("pipeline_running", False)}
    except Exception:
        return {"online": False, "pipeline_running": False, "reason": "Robot PC unreachable"}


@router.post("/command", response_model=schemas.RobotCommandResponse)
async def send_command(
    command: schemas.RobotCommand,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    if command.command not in ("start", "pause", "stop"):
        raise HTTPException(status_code=400, detail="command must be start, pause, or stop")

    # The Robot PC only has /start and /stop — there's no true "pause",
    # so pause behaves identically to stop for now.
    endpoint = "start" if command.command == "start" else "stop"
    robot_url = await get_robot_pc_url(db)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{robot_url}/{endpoint}")
            response.raise_for_status()
            return schemas.RobotCommandResponse(
                success=True,
                message=f"Command '{command.command}' sent successfully",
                robot_response=response.json(),
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Could not reach Robot PC: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Robot PC returned an error: {e.response.text}")


@router.get("/parameters")
async def get_parameters(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    robot_url = await get_robot_pc_url(db)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{robot_url}/parameters")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Could not reach Robot PC: {str(e)}")


@router.post("/parameters", response_model=schemas.RobotCommandResponse)
async def send_parameters(
    params: schemas.RobotParameters,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role(UserRole.operator)),
):
    robot_url = await get_robot_pc_url(db)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{robot_url}/parameters", json=params.model_dump())
            response.raise_for_status()
            return schemas.RobotCommandResponse(
                success=True,
                message="Parameters updated",
                robot_response=response.json(),
            )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Could not reach Robot PC: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Robot PC returned an error: {e.response.text}")
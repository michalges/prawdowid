from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status

from prawdowid.api.deps import ServicesDep, get_client_key
from prawdowid.schemas import CheckRequest, CheckResult, SessionDeletion

router = APIRouter(prefix="/v1", tags=["checks"])


@router.post("/checks")
async def create_check(
    check_request: CheckRequest,
    services: ServicesDep,
    client_key: Annotated[str | None, Depends(get_client_key)],
) -> CheckResult:
    return await services.pipeline.run(check_request, client_key)


@router.get("/checks/{check_id}")
async def get_check(check_id: UUID, services: ServicesDep) -> CheckResult:
    result_json = services.database.get_check_result_json(str(check_id))
    if result_json is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Nie znaleziono sprawdzenia (mogło zostać usunięte)."
        )
    return CheckResult.model_validate_json(result_json)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: Annotated[str, Path(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")],
    services: ServicesDep,
) -> SessionDeletion:
    deleted = services.database.delete_session(session_id)
    services.pipeline.cache.clear()
    return SessionDeletion(session_id=session_id, deleted=deleted)

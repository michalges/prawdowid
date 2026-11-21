import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from prawdowid.services import Services


def get_services(request: Request) -> Services:
    return request.app.state.services


def require_admin(
    services: Annotated[Services, Depends(get_services)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    token = services.settings.admin_token
    if token is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "ADMIN_TOKEN is not configured")
    expected = f"Bearer {token.get_secret_value()}"
    if not authorization or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid admin token")


def get_client_key(request: Request) -> str | None:
    return request.client.host if request.client else None


ServicesDep = Annotated[Services, Depends(get_services)]
AdminDep = Annotated[None, Depends(require_admin)]

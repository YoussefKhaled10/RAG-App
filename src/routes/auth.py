from fastapi import APIRouter, Depends, HTTPException, Request, status

from controllers.AuthController import AuthController
from dependencies.auth import get_current_user
from schemas.auth import (
    CurrentUserResponse,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from schemas.registration import TenantRegistrationRequest
from services.registration import RegistrationConflictError


auth_router = APIRouter(
    prefix="/api/v1/auth",
    tags=["api_v1", "auth"],
)


@auth_router.post(
    "/register-tenant",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_tenant(
    request: Request,
    registration_data: TenantRegistrationRequest,
) -> TokenResponse:
    auth_controller = await AuthController.create_instance(
        db_client=request.app.db_client,
    )

    try:
        return await auth_controller.register_tenant(
            registration_data=registration_data,
        )
    except RegistrationConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def login(
    request: Request,
    login_data: LoginRequest,
) -> TokenResponse:
    auth_controller = await AuthController.create_instance(
        db_client=request.app.db_client,
    )

    try:
        return await auth_controller.login(
            login_data=login_data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
async def refresh_tokens(
    request: Request,
    refresh_data: RefreshTokenRequest,
) -> TokenResponse:
    auth_controller = await AuthController.create_instance(
        db_client=request.app.db_client,
    )

    try:
        return await auth_controller.refresh_tokens(
            refresh_token=refresh_data.refresh_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@auth_router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
)
async def read_current_user(
    current_user: CurrentUserResponse = Depends(get_current_user),
) -> CurrentUserResponse:
    return current_user

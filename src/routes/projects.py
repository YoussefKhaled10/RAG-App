from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from dependencies.auth import (
    get_current_user,
    require_tenant_admin,
)
from models.ProjectModel import ProjectModel
from models.db_schemes import Project
from schemas.auth import CurrentUserResponse
from schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)


projects_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["projects"],
)


async def _get_project_model(
    request: Request,
) -> ProjectModel:
    return await ProjectModel.create_instance(
        db_client=request.app.db_client,
    )


def _to_project_response(
    project: Project,
) -> ProjectResponse:
    return ProjectResponse.model_validate(project)


@projects_router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    request: Request,
    project_data: ProjectCreate,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> ProjectResponse:
    tenant_id = current_user.user.tenant_id
    project_model = await _get_project_model(request)

    existing_project = (
        await project_model.get_project_by_name(
            tenant_id=tenant_id,
            project_name=project_data.project_name,
        )
    )
    if existing_project is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "a project with this name already exists "
                "inside the tenant"
            ),
        )

    project_record = Project(
        tenant_id=tenant_id,
        project_name=project_data.project_name,
        project_description=(
            project_data.project_description
        ),
    )

    try:
        created_project = (
            await project_model.create_project(
                project=project_record,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _to_project_response(created_project)


@projects_router.get(
    "",
    response_model=ProjectListResponse,
)
async def list_projects(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: CurrentUserResponse = Depends(
        get_current_user
    ),
) -> ProjectListResponse:
    tenant_id = current_user.user.tenant_id
    project_model = await _get_project_model(request)

    projects, total, total_pages = (
        await project_model.get_all_projects(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
        )
    )

    return ProjectListResponse(
        items=[
            _to_project_response(project)
            for project in projects
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@projects_router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def get_project(
    request: Request,
    project_id: int,
    current_user: CurrentUserResponse = Depends(
        get_current_user
    ),
) -> ProjectResponse:
    tenant_id = current_user.user.tenant_id
    project_model = await _get_project_model(request)

    project = await project_model.get_project_by_id(
        tenant_id=tenant_id,
        project_id=project_id,
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )

    return _to_project_response(project)


@projects_router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def update_project(
    request: Request,
    project_id: int,
    project_data: ProjectUpdate,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> ProjectResponse:
    tenant_id = current_user.user.tenant_id
    project_model = await _get_project_model(request)
    update_data = project_data.model_dump(
        exclude_unset=True,
    )

    existing_project = (
        await project_model.get_project_by_id(
            tenant_id=tenant_id,
            project_id=project_id,
        )
    )
    if existing_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )

    new_name = update_data.get("project_name")
    if (
        new_name is not None
        and new_name != existing_project.project_name
    ):
        project_with_same_name = (
            await project_model.get_project_by_name(
                tenant_id=tenant_id,
                project_name=new_name,
            )
        )
        if project_with_same_name is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "a project with this name already "
                    "exists inside the tenant"
                ),
            )

    try:
        updated_project = (
            await project_model.update_project(
                tenant_id=tenant_id,
                project_id=project_id,
                project_name=new_name,
                project_description=update_data.get(
                    "project_description"
                ),
                update_description=(
                    "project_description" in update_data
                ),
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if updated_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )

    return _to_project_response(updated_project)


@projects_router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    request: Request,
    project_id: int,
    current_user: CurrentUserResponse = Depends(
        require_tenant_admin
    ),
) -> None:
    tenant_id = current_user.user.tenant_id
    project_model = await _get_project_model(request)

    deleted = await project_model.delete_project(
        tenant_id=tenant_id,
        project_id=project_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="project not found",
        )

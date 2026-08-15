from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .BaseDataModel import BaseDataModel
from .db_schemes import Project, Tenant


class ProjectModel(BaseDataModel):
    def __init__(self, db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(
        cls,
        db_client: object,
    ) -> "ProjectModel":
        return cls(db_client=db_client)

    async def create_project(
        self,
        project: Project,
    ) -> Project:
        try:
            async with self.db_client() as session:
                tenant_query = select(
                    Tenant.tenant_id
                ).where(
                    Tenant.tenant_id == project.tenant_id,
                    Tenant.tenant_status == "active",
                )
                tenant_result = await session.execute(
                    tenant_query
                )

                if tenant_result.scalar_one_or_none() is None:
                    raise ValueError(
                        "active tenant not found"
                    )

                project.project_name = " ".join(
                    project.project_name.split()
                )

                session.add(project)
                await session.commit()
                await session.refresh(project)
                return project

        except IntegrityError as exc:
            raise ValueError(
                "project name already exists in this tenant"
            ) from exc
        except SQLAlchemyError:
            raise

    async def get_project_by_id(
        self,
        tenant_id: UUID,
        project_id: int,
    ) -> Project | None:
        async with self.db_client() as session:
            query = select(Project).where(
                Project.project_id == project_id,
                Project.tenant_id == tenant_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_project_by_uuid(
        self,
        tenant_id: UUID,
        project_uuid: UUID,
    ) -> Project | None:
        async with self.db_client() as session:
            query = select(Project).where(
                Project.project_uuid == project_uuid,
                Project.tenant_id == tenant_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_project_by_name(
        self,
        tenant_id: UUID,
        project_name: str,
    ) -> Project | None:
        normalized_name = " ".join(
            project_name.split()
        )

        async with self.db_client() as session:
            query = select(Project).where(
                Project.tenant_id == tenant_id,
                Project.project_name == normalized_name,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_all_projects(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Project], int, int]:
        safe_page = max(page, 1)
        safe_page_size = min(
            max(page_size, 1),
            100,
        )

        async with self.db_client() as session:
            count_query = select(
                func.count(Project.project_id)
            ).where(
                Project.tenant_id == tenant_id
            )
            count_result = await session.execute(
                count_query
            )
            total_projects = count_result.scalar_one()
            total_pages = (
                total_projects + safe_page_size - 1
            ) // safe_page_size

            query = (
                select(Project)
                .where(Project.tenant_id == tenant_id)
                .order_by(Project.created_at.desc())
                .offset(
                    (safe_page - 1) * safe_page_size
                )
                .limit(safe_page_size)
            )
            result = await session.execute(query)
            projects = list(result.scalars().all())

            return projects, total_projects, total_pages

    async def update_project(
        self,
        tenant_id: UUID,
        project_id: int,
        project_name: str | None = None,
        project_description: str | None = None,
        update_description: bool = False,
    ) -> Project | None:
        try:
            async with self.db_client() as session:
                query = select(Project).where(
                    Project.project_id == project_id,
                    Project.tenant_id == tenant_id,
                )
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if project is None:
                    return None

                if project_name is not None:
                    project.project_name = " ".join(
                        project_name.split()
                    )

                if update_description:
                    project.project_description = (
                        project_description
                    )

                await session.commit()
                await session.refresh(project)
                return project

        except IntegrityError as exc:
            raise ValueError(
                "project name already exists in this tenant"
            ) from exc
        except SQLAlchemyError:
            raise

    async def delete_project(
        self,
        tenant_id: UUID,
        project_id: int,
    ) -> bool:
        try:
            async with self.db_client() as session:
                query = select(Project).where(
                    Project.project_id == project_id,
                    Project.tenant_id == tenant_id,
                )
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if project is None:
                    return False

                await session.delete(project)
                await session.commit()
                return True

        except SQLAlchemyError:
            raise

    async def project_exists(
        self,
        tenant_id: UUID,
        project_id: int,
    ) -> bool:
        async with self.db_client() as session:
            query = select(Project.project_id).where(
                Project.project_id == project_id,
                Project.tenant_id == tenant_id,
            )
            result = await session.execute(query)
            return result.scalar_one_or_none() is not None

from pathlib import Path
from uuid import UUID

from .BaseController import BaseController


class ProjectController(BaseController):

    def __init__(self):
        super().__init__()

    def get_project_path(
        self,
        tenant_id: UUID,
        project_id: int,
    ) -> str:

        if project_id <= 0:
            raise ValueError(
                "project_id must be positive"
            )

        base_directory = Path(
            self.files_dir
        ).resolve()

        tenant_directory = (
            base_directory
            / str(tenant_id)
        )

        project_directory = (
            tenant_directory
            / str(project_id)
        )

        resolved_project_directory = (
            project_directory.resolve()
        )

        if (
            base_directory
            not in resolved_project_directory.parents
        ):
            raise ValueError(
                "invalid project path"
            )

        resolved_project_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        return str(
            resolved_project_directory
        )
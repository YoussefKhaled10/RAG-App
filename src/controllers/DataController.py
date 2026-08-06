import re
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from helpers.config import get_settings
from models import ResponseSignal

from .BaseController import BaseController
from .ProjectController import ProjectController


class DataController(BaseController):
    def __init__(self):
        super().__init__()
        self.settings = get_settings()

    def _allowed_extensions(self) -> set[str]:
        raw_types = self.settings.FILE_ALLOWED_TYPES

        if isinstance(raw_types, str):
            values = re.split(r"[,;| ]+", raw_types)
        else:
            values = list(raw_types)

        return {
            str(value).strip().lower().lstrip(".")
            for value in values
            if str(value).strip()
        }

    def validate_uploaded_file(
        self,
        file: UploadFile,
    ) -> tuple[bool, str]:

        if file is None or not file.filename:
            return (
                False,
                ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value,
            )

        safe_file_name = Path(
            file.filename
        ).name

        file_extension = Path(
            safe_file_name
        ).suffix.lower()

        content_type = (
            file.content_type
            or ""
        ).strip().lower()

        allowed_content_types = {
            str(allowed_type).strip().lower()
            for allowed_type
            in self.settings.FILE_ALLOWED_TYPES
        }

        extension_content_types = {
            ".pdf": {
                "application/pdf",
            },
            ".txt": {
                "text/plain",
                "application/octet-stream",
            },
        }

        allowed_extensions = {
            extension
            for extension, content_types
            in extension_content_types.items()
            if content_types & allowed_content_types
        }

        if file_extension not in allowed_extensions:
            return (
                False,
                ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value,
            )

        expected_content_types = (
            extension_content_types.get(
                file_extension,
                set(),
            )
        )

        if (
            content_type
            and content_type
            not in expected_content_types
        ):
            return (
                False,
                ResponseSignal.FILE_TYPE_NOT_SUPPORTED.value,
            )

        declared_size = getattr(
            file,
            "size",
            None,
        )

        if (
            declared_size is not None
            and declared_size
            > self.settings.FILE_MAX_SIZE
        ):
            return (
                False,
                ResponseSignal.FILE_SIZE_EXCEEDED.value,
            )

        return (
            True,
            ResponseSignal.FILE_VALIDATED_SUCCESS.value,
        )

    def generate_unique_filepath(
        self,
        original_file_name: str,
        tenant_id: UUID,
        project_id: int,
    ) -> tuple[str, str]:
        safe_original_name = Path(
            original_file_name or "uploaded-file"
        ).name

        extension = Path(safe_original_name).suffix.lower()
        if not extension:
            raise ValueError("file extension is required")

        stored_file_name = f"{uuid.uuid4().hex}{extension}"

        project_directory = Path(
            ProjectController().get_project_path(
                tenant_id=tenant_id,
                project_id=project_id,
            )
        ).resolve()
        project_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        file_path = (
            project_directory / stored_file_name
        ).resolve()

        if file_path.parent != project_directory:
            raise ValueError("invalid file path")

        return str(file_path), stored_file_name

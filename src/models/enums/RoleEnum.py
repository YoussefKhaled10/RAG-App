from enum import Enum


class RoleName(str, Enum):
    TENANT_ADMIN = "Tenant Admin"
    DOCUMENT_MANAGER = "Document Manager"
    VIEWER = "Viewer"


ROLE_DESCRIPTIONS: dict[RoleName, str] = {
    RoleName.TENANT_ADMIN: (
        "Full administrative access inside the tenant. Can manage "
        "users, roles, projects, documents, and tenant resources."
    ),
    RoleName.DOCUMENT_MANAGER: (
        "Can upload, process, and manage documents inside tenant projects."
    ),
    RoleName.VIEWER: (
        "Read-only access. Can view tenant resources and ask questions."
    ),
}


ROLE_PERMISSIONS: dict[RoleName, list[str]] = {
    RoleName.TENANT_ADMIN: [
        "manage_users",
        "manage_roles",
        "manage_projects",
        "manage_documents",
        "view_documents",
        "ask_questions",
    ],
    RoleName.DOCUMENT_MANAGER: [
        "manage_documents",
        "view_documents",
        "ask_questions",
    ],
    RoleName.VIEWER: [
        "view_documents",
        "ask_questions",
    ],
}
from enum import Enum

from auth.permission import Permission


class Role(str, Enum):
    SUPERADMIN = "superadmin"
    INSTRUCTOR = "instructor"
    ESTUDIANTE = "estudiante"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.SUPERADMIN: frozenset(Permission),
    Role.INSTRUCTOR: frozenset(
        {
            Permission.READ_USERS,
            Permission.UPDATE_USERS,
            Permission.READ_OWN_PROFILE,
            Permission.UPDATE_OWN_PROFILE,
            Permission.UPLOAD_EXCEL,
        }
    ),
    Role.ESTUDIANTE: frozenset(
        {
            Permission.READ_OWN_PROFILE,
            Permission.UPDATE_OWN_PROFILE,
        }
    ),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
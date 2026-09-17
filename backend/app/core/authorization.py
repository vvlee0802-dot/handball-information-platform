from enum import StrEnum

from app.models.user import User


class UserRole(StrEnum):
    ATHLETE = "athlete"
    COACH_ANALYST = "coach_analyst"
    COMPETITION_ADMIN = "competition_admin"
    SYSTEM_ADMIN = "system_admin"


class Permission(StrEnum):
    VIEW_AUTHORIZED_VIDEO = "view_authorized_video"
    UPLOAD_AND_ANNOTATE_VIDEO = "upload_and_annotate_video"
    MANAGE_COMPETITION_DATA = "manage_competition_data"
    GENERATE_REPORTS = "generate_reports"
    MANAGE_USERS = "manage_users"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ATHLETE: {Permission.VIEW_AUTHORIZED_VIDEO},
    UserRole.COACH_ANALYST: {
        Permission.VIEW_AUTHORIZED_VIDEO,
        Permission.UPLOAD_AND_ANNOTATE_VIDEO,
        Permission.GENERATE_REPORTS,
    },
    UserRole.COMPETITION_ADMIN: {
        Permission.VIEW_AUTHORIZED_VIDEO,
        Permission.MANAGE_COMPETITION_DATA,
    },
    UserRole.SYSTEM_ADMIN: set(Permission),
}


def get_effective_permissions(user: User) -> set[Permission]:
    try:
        role = UserRole(user.role)
    except ValueError:
        return set()

    permissions = set(ROLE_PERMISSIONS[role])
    for grant in user.permission_grants:
        try:
            permissions.add(Permission(grant.permission))
        except ValueError:
            continue
    return permissions


def has_permission(user: User, permission: Permission) -> bool:
    return permission in get_effective_permissions(user)

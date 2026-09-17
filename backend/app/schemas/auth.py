from pydantic import BaseModel, Field

from app.core.authorization import Permission, UserRole, get_effective_permissions
from app.models.user import User


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    id: int
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    permissions: list[Permission]


def to_user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=UserRole(user.role),
        is_active=user.is_active,
        permissions=sorted(get_effective_permissions(user), key=str),
    )

from pydantic import BaseModel, Field

from app.core.authorization import Permission, UserRole


class AdminUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.ATHLETE
    extra_permissions: list[Permission] = Field(default_factory=list)


class AdminUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None
    extra_permissions: list[Permission] | None = None


class AdminUserRead(BaseModel):
    id: int
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    permissions: list[Permission]
    extra_permissions: list[Permission]

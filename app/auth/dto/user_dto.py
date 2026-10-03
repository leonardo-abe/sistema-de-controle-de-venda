from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.auth.enum.role_permissions import RolePermissions


class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: RolePermissions = RolePermissions.VIEWER


class UserCreateSchema(UserBase):
    password: str = Field(min_length=6)


class UserUpdateSchema(BaseModel):
    name: str | None = None
    role: RolePermissions | None = None
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=6)


class UserSchema(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginSchema(BaseModel):
    email: EmailStr
    password: str

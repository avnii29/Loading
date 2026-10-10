from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole, DonorType


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    role: UserRole
    donor_type: DonorType | None = None
    organization_name: str | None = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(min_length=2, max_length=255)
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: str | None = None
    role: str
    donor_type: str | None = None
    organization_name: str | None = None
    organization_id: str | None = None
    verification_status: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)


def to_user_response(user) -> UserResponse:
    profile = user.profile
    org = getattr(user, "organization", None)
    partner = getattr(user, "recovery_partner", None)
    organization_name = None
    organization_id = None
    verification = None
    if org:
        organization_name = org.name
        organization_id = str(org.id)
        verification = org.verification_status.value
    elif partner:
        organization_name = partner.name
        organization_id = str(partner.id)
        verification = partner.verification_status.value

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=profile.full_name if profile else "",
        phone=profile.phone if profile else None,
        role=user.role.value,
        donor_type=profile.donor_type.value if profile and profile.donor_type else None,
        organization_name=organization_name,
        organization_id=organization_id,
        verification_status=verification,
    )

"""
Pydantic schemas for authentication endpoints
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class LoginRequest(BaseModel):
    """Login request payload"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="At least 8 characters")
    full_name: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=100, description="Organization/tenant identifier")


class TokenResponse(BaseModel):
    """Token response for login/refresh endpoints"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str = Field(..., min_length=1)


class UserOut(BaseModel):
    """User output schema (public representation)"""
    id: int
    email: str
    full_name: str | None
    tenant_id: str
    is_admin: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


_REGIMES = {"lucro_real", "lucro_presumido", "simples_nacional"}


class OnboardingRequest(BaseModel):
    """Onboarding wizard payload — fiscal identity for a tenant"""
    cnpj: str = Field(..., min_length=14, max_length=18, description="CNPJ (digits only or formatted XX.XXX.XXX/XXXX-XX)")
    razao_social: str = Field(..., min_length=1, max_length=255)
    uf: str = Field(..., min_length=2, max_length=2, description="UF do estabelecimento principal (e.g. SP)")
    regime_tributario: str = Field(..., description="lucro_real | lucro_presumido | simples_nacional")

    def model_post_init(self, __context) -> None:
        if self.regime_tributario not in _REGIMES:
            raise ValueError(f"regime_tributario must be one of {sorted(_REGIMES)}")


class OnboardingStatusResponse(BaseModel):
    """Response for GET /auth/onboarding/status"""
    completed: bool
    regime_tributario: str | None = None

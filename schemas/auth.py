from pydantic import BaseModel, EmailStr, Field, field_validator


# Requests
class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str


class UserRegisterSchema(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=20)
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        if len(v) < 8:
            raise ValueError("Password too short, must be at least 8 characters")

        if len(v) > 64:
            raise ValueError("Password too long, must be at most 64 characters")

        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain a letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain a digit")

        return v


# Responses
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    email_verified: bool


class RefreshResponse(BaseModel):
    access_token: str


class ProfileResponse(BaseModel):
    username: str
    email_verified: bool
    avatar: str | None
    skills: int
    total_tests: int
    average_score: int


class UpdateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20)



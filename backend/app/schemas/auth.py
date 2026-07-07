import re
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from app.core.security import contains_html


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator('username')
    @classmethod
    def validate_username_no_xss(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError('用户名不能超过 100 个字符')
        if contains_html(v):
            raise ValueError('用户名不能包含 HTML 标签')
        return v

    @field_validator('email')
    @classmethod
    def validate_email_no_xss(cls, v: str) -> str:
        if contains_html(v):
            raise ValueError('邮箱不能包含 HTML 标签')
        return v

    @model_validator(mode='after')
    def validate_password_strength(self):
        v = self.password
        if len(v) < 8:
            raise ValueError('密码至少需要 8 个字符')
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError('密码必须包含字母')
        if not re.search(r'[0-9]', v):
            raise ValueError('密码必须包含数字')
        return self


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str = ""
    token_type: str = "bearer"
    user: UserResponse

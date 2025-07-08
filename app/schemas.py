from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str

    @field_validator('password')
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError('Пароль не может быть короче 8 символов!')
        if value.lower() == value:
            raise ValueError('Пароль должен содержать строчные и прописные буквы!')
        digits = False
        letters = False

        for letter in value:
            if letter.isdigit():
                digits = True
            else:
                letters = True
        if digits and letters:
            pass
        else:
            raise ValueError('Пароль должен содержать буквы и цифры!')
        return value

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    username: str
    created_at: datetime

    class Config:
        from_attributes = True

class ContactCreate(BaseModel):
    contact_id: int

class ContactResponse(BaseModel):
    id: int
    contact_id: int
    username: str  # Имя контакта

    class Config:
        from_attributes = True

class Message(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    text: str
    timestamp: datetime
    is_delivered: bool
    is_read: bool

    class Config:
        from_attributes = True
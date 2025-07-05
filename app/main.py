import logging
from email.policy import default

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, security
from app.database import SessionLocal
from datetime import datetime
from app.schemas import UserCreate, UserLogin, Token, UserResponse
from fastapi.security import OAuth2PasswordBearer

logger = logging.getLogger(__name__)
app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Декорируем токен
    payload = security.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

    # Извлекаем username из токена
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

    # Ищем пользователя в базе данных
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return user

@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    # Проверка пользователя на существование в базе данных
    existing_user = db.query(models.User).filter(models.User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    # Хэшируем пароль
    hashed_password = security.get_password_hash(user.password)

    # Создаем нового пользователя
    new_user = models.User(
        username=user.username,
        hashed_password=hashed_password)

    # Сохраняем нового пользователя в базе данных
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Возвращаем ответ без пароля
    return UserResponse(
        username=new_user.username,
        created_at=datetime.now()
    )

@app.post("/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    # Поиск пользователя в базе, вызов исключения в случае его отсутствия
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if not db_user:
        raise HTTPException(401, detail='Неверное имя пользователя или пароль!')

    # Вызов исключения также в случае неверного ввода пароля
    if not security.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(401, detail='Неверное имя пользователя или пароль!')

    # Создаем токен
    try:
        access_token = security.create_access_token(data={"sub": db_user.username})
        # Возвращаем токен
        return Token(
            access_token=access_token,
            token_type='bearer')
    except ValueError as e:
        raise HTTPException(status_code=500, detail="Ошибка сервера при создании токена")

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user



import logging
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, security
from app.database import SessionLocal
from datetime import datetime
from app.schemas import UserCreate, UserLogin, Token, UserResponse

logger = logging.getLogger(__name__)
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
    elif not security.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(401, detail='Неверное имя пользователя или пароль!')

    # Создаем токен
    else:
        try:
            access_token = security.create_access_token(data={"sub": db_user.username})
            # Возвращаем токен
            return Token(
                access_token=access_token,
                token_type='bearer')
        except ValueError as e:
            raise HTTPException(status_code=500, detail="Ошибка сервера при создании токена")

'''
@app.post("/users/me")
#async def register(user: UserCreate, db: Session = Depends(get_db)):
    #pass
# Ваша реализация здесь'''


import json
import logging
from email.policy import default
from idlelib.query import Query

from fastapi import FastAPI, Depends, HTTPException, Query, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.websockets import WebSocket, WebSocketDisconnect

from app import models, schemas, security, crud
from app.database import SessionLocal
from datetime import datetime
from app.schemas import UserCreate, UserLogin, Token, UserResponse
from fastapi.security import OAuth2PasswordBearer

from typing import List

from app import connection_manager

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
        hashed_password=hashed_password,
        created_at=datetime.utcnow())

    # Сохраняем нового пользователя в базе данных
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Возвращаем ответ без пароля
    return UserResponse(
        id=new_user.id,
        username=new_user.username,
        created_at=datetime.now(),
        is_online=new_user.is_online
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
        access_token = security.create_access_token(data={"sub": db_user.username, "user_id": db_user.id})
        # Возвращаем токен
        return Token(
            access_token=access_token,
            token_type='bearer')
    except ValueError as e:
        raise HTTPException(status_code=500, detail="Ошибка сервера при создании токена")

@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at,
        "is_online": current_user.is_online
    }

@app.websocket("/chat")
async def websocket_endpoint(
        websocket: WebSocket,
        token: str = Query(...),
        db: Session = Depends(get_db)
):
    try:
        payload = security.decode_token(token)
        if not payload:
            await websocket.close(code=1008)
            return

        # Исправляем получение имени пользователя
        username = payload.get("sub")
        if not username:
            await websocket.close(code=1008)
            return

        # Получаем user_id из базы данных
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            await websocket.close(code=1008)
            return

        user_id = str(user.id)

    except Exception as e:
        logger.error(f"Ошибка аутентификации: {str(e)}")
        await websocket.close(code=1008)
        return

    manager = connection_manager.ConnectionManager(db)
    await manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_text()
            # обработка сообщения
            message = json.loads(data)

            # Определение типа сообщения
            if message["type"] == "private":
                await manager.send_to_user(
                    json.dumps(message),
                    message["receiver"])

            # При получении сообщения
            new_message = models.Message(
                sender_id=message["sender"],
                receiver_id=message["receiver"],
                text=message["text"],
                timestamp=datetime.utcnow()
            )
            db.add(new_message)
            db.commit()

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except json.JSONDecodeError:
        await websocket.send_text("Ошибка: Неверный формат сообщения")

# Эндпоинты для обработки контактов
@app.post("/contacts", response_model=schemas.ContactResponse)
async def add_contact(
        contact: schemas.ContactCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Проверяем, существует ли контакт
    db_contact_user = db.query(models.User).filter(models.User.id == contact.contact_id).first()
    if not db_contact_user:
        raise HTTPException(404, "Пользователь не найден")

    # Проверяем, не добавлен ли уже контакт
    existing_contact = db.query(models.Contact).filter(
        models.Contact.user_id == current_user.id,
        models.Contact.contact_id == contact.contact_id
    ).first()

    if existing_contact:
        raise HTTPException(400, "Контакт уже добавлен")

    # Создаем новую запись контакта
    new_contact = models.Contact(
        user_id=current_user.id,
        contact_id=contact.contact_id
    )

    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)

    return {
        "id": new_contact.id,
        "contact_id": new_contact.contact_id,
        "username": db_contact_user.username
    }

@app.get("/contacts", response_model=List[schemas.ContactResponse])
async def get_contacts(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    return crud.get_user_contacts(db, current_user.id)

# main.py
@app.get("/messages", response_model=List[schemas.Message])
async def get_messages(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    messages = db.query(models.Message).filter(
        ((models.Message.sender_id == current_user.id) &
         (models.Message.receiver_id == contact_id)) |
        ((models.Message.sender_id == contact_id) &
         (models.Message.receiver_id == current_user.id))
    ).order_by(models.Message.timestamp.asc()).all()
    return messages
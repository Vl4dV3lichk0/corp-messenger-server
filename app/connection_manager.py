import json
import asyncio
from fastapi import WebSocket
from typing import Dict, List, Optional
from app.crud import get_user_contacts  # Импорт функции
from sqlalchemy.orm import Session

class ConnectionManager:
    def __init__(self, db: Optional[Session] = None):
        # Основное хранилище: user_id -> список WebSocket-соединений
        self.active_connections: Dict[str, List[WebSocket]] = {}

        # Для быстрого поиска пользователя по соединению
        self.connection_to_user: Dict[WebSocket, str] = {}

        # Блокировка для потокобезопасности
        self.lock = asyncio.Lock()

        # Для групповых чатов group_id → список user_id
        self.group_connections: Dict[str, List[str]] = {}

        # user_id → online status
        self.user_status: Dict[str, bool] = {}

        self.db = db

    async def notify_status(self, user_id: str, status: str):
        """Уведомляет контакты пользователя об изменении статуса"""
        if not self.db:
            return  # Без сессии БД уведомления невозможны

        contacts = get_user_contacts(self.db, int(user_id))
        for contact in contacts:
            contact_id = str(contact["contact_id"])
            await self.send_to_user(
                json.dumps({
                    "type": "status",
                    "user_id": user_id,
                    "status": status
                }),
                contact_id
            )

    async def connect(self, websocket: WebSocket, user_id: str):
        # Принимаем соединение
        await websocket.accept()

        # Регистрируем соединение (потокобезопасно)
        async with self.lock:
            # Для нового пользователя создаем пустой список
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []

            # Добавляем соединение в список пользователя
            self.active_connections[user_id].append(websocket)

            # Сохраняем обратное отображение
            self.connection_to_user[websocket] = user_id

        # Отправляем уведомление о подключении
        await self.send_personal_message(
            f"Вы подключены! Ваш ID: {user_id}",
            websocket
        )
        await self.notify_status(user_id, "online")

        self.user_status[user_id] = True  # Помечаем как онлайн

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            user_id = self.connection_to_user.get(websocket)
            if user_id:
                if websocket in self.active_connections.get(user_id, []):
                    self.active_connections[user_id].remove(websocket)
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]
                del self.connection_to_user[websocket]
                self.user_status[user_id] = False
                await self.notify_status(user_id, "offline")
                self.user_status[user_id] = False  # Помечаем как офлайн


    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_to_user(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id]:
                await websocket.send_text(message)
from fastapi import WebSocket
from typing import Dict, List
import asyncio
import requests
from app import schemas, security

class ConnectionManager:
    def __init__(self):
        # Основное хранилище: user_id -> список WebSocket-соединений
        self.active_connections: Dict[str, List[WebSocket]] = {}

        # Для быстрого поиска пользователя по соединению
        self.connection_to_user: Dict[WebSocket, str] = {}

        # Блокировка для потокобезопасности
        self.lock = asyncio.Lock()

        # Для групповых чатов group_id → список user_id
        self.group_connections: Dict[str, List[str]] = {}


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

        # Обновляем статус пользователя (в БД)
        # ... здесь будет обращение к БД ...

        # Отправляем уведомление о подключении
        await self.send_personal_message(
            f"Вы подключены! Ваш ID: {user_id}",
            websocket
        )

        # Уведомляем контакты
        #await self.notify_user_status(user_id, "online")

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            user_id = self.connection_to_user.get(websocket)
            if user_id:
                self.active_connections[user_id].remove(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                del self.connection_to_user[websocket]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        pass

    async def broadcast(self, message: str):
        pass
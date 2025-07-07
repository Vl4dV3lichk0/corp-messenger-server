from sqlalchemy.orm import Session
from . import models, schemas


def get_user_contacts(db: Session, user_id: int):
    """Возвращает список контактов с информацией о пользователях"""
    contacts = db.query(models.Contact).filter(models.Contact.user_id == user_id).all()

    result = []
    for contact in contacts:
        # Получаем информацию о контакте
        contact_info = {
            "id": contact.id,
            "contact_id": contact.contact_id,
            "username": contact.contact.username,
            "is_online": False  # Заглушка, будет заполнено позже
        }
        result.append(contact_info)

    return result
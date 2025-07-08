from passlib.hash import bcrypt
import logging
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv, dotenv_values

logger = logging.getLogger(__name__)

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES = os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES')

if not SECRET_KEY:
    raise ValueError("SECRET_KEY не найден в .env")

def get_password_hash(password: str) -> str or False:
    """Generating a hash of a password"""
    try:
        if not password:
            raise ValueError("Пароль не может быть пустым!")
        hashed_password = bcrypt.hash(password)
        return hashed_password
    except Exception as e:
        logger.error(f"Ошибка хеширования пароля: {str(e)}")
        return False

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifying password against a hashed password"""
    try:
        verified = bcrypt.verify(plain_password, hashed_password)
        return verified
    except Exception as e:
        logger.error(f"Ошибка верификации пароля: {str(e)}")
        return False

def create_access_token(data: dict) -> str:
    """Create an access token"""
    try:
        payload = {
            "sub": data.get("sub"),
            "user_id": data.get("user_id"),
        }
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload.update({"exp": expire})
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token
    except Exception as e:
        logger.error(f"Ошибка генерации токена JWT: {str(e)}")
        raise ValueError("Ошибка при создании токена")

def decode_token(token: str) -> dict or None:
    """Decode a token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        return payload
    except jwt.ExpiredSignatureError:
        logger.error('Срок действия токена JWT истек.')
        return None

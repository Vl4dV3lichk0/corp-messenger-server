from passlib.hash import bcrypt
import logging
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv, dotenv_values

logger = logging.getLogger(__name__)

ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 30

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
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
        payload = {"sub": data.get("sub")}
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

if __name__ == '__main__':
    # Тест
    '''h = get_password_hash('As2Werd76as!')
    print(verify_password( 'As2Werd76as!', h))

    data = {'sub': 'Vlad', 'message': 'content'}
    token = create_access_token(data=data)
    print(data)
    print(token)
    print(decode_token(token))'''

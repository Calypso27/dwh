"""
Authentification JWT — implémente les 2 niveaux d'administration du
cahier des charges :
  - institution_admin : vue globale, toutes les sources/organisations
  - scoped_admin       : limité à une seule source (school_id / source_id)

Les comptes sont lus depuis la table dim_user (mots de passe hashés en
base), plus de comptes codés en dur dans l'application.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import duckdb
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from api.schemas import CurrentUser
from dw.paths import DB_PATH

SECRET_KEY = "change-moi-en-production-via-variable-environnement"  # nosec - MVP uniquement
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def _get_user_row(username: str) -> Optional[dict]:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        row = con.execute(
            "SELECT username, hashed_password, role, scope_source_id, is_active "
            "FROM dim_user WHERE username = ? AND is_current = true",
            [username],
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    return {
        "username": row[0], "hashed_password": row[1], "role": row[2],
        "scope_source_id": row[3], "is_active": row[4],
    }


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    user = _get_user_row(username)
    if not user or not user["is_active"] or not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou expirés",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = _get_user_row(username)
    if user is None or not user["is_active"]:
        raise credentials_exception

    return CurrentUser(username=user["username"], role=user["role"], scope_source_id=user["scope_source_id"])


def require_institution_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "institution_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé à l'administrateur global")
    return current_user

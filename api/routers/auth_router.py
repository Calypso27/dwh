from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from api.auth import authenticate_user, create_access_token, get_current_user
from api.schemas import Token, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user["username"], "role": user["role"], "scope_source_id": user["scope_source_id"]}
    )
    return Token(access_token=token)


@router.get("/me", response_model=CurrentUser)
def read_current_user(current_user: CurrentUser = Depends(get_current_user)):
    return current_user

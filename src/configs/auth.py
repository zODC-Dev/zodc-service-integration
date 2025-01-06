from fastapi.security import OAuth2PasswordBearer

from src.configs.settings import settings

# Centralize OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/token",
    scheme_name="JWT",
    description="JWT authentication"
)

# JWT Configuration
JWT_SETTINGS = {
    "SECRET_KEY": settings.JWT_SECRET,
    "ALGORITHM": settings.JWT_ALGORITHM,
    "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
    "REFRESH_TOKEN_EXPIRE_DAYS": 7,
}

import pytest
import os


def test_missing_api_secret_key_raises_error():
    """
    Проверяем что Pydantic Settings падает без API_SECRET_KEY.
    """
    # Сохраняем текущее значение
    original = os.environ.pop("API_SECRET_KEY", None)
    
    try:
        # Пересоздаём Settings — должен быть ValidationError
        from app.config import Settings
        
        with pytest.raises(Exception) as exc_info:
            Settings(_env_file=None)
        
        # Проверяем что это ValidationError от Pydantic (по отсутствующему полю)
        assert "API_SECRET_KEY" in str(exc_info.value) or "validation error" in str(exc_info.value).lower()
    
    finally:
        # Восстанавливаем
        if original:
            os.environ["API_SECRET_KEY"] = original

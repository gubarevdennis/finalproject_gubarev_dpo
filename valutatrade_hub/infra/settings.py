# valutatrade_hub/infra/settings.py
import json
import os
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class SettingsLoader:
    """
    Singleton для загрузки и хранения настроек приложения
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_settings()
        return cls._instance

    def _load_settings(self):
        """Загружает настройки из файла или использует значения по умолчанию"""
        self._settings = {
            'data_dir': os.path.join(BASE_DIR, "data"),
            'rates_ttl_seconds': 300,  # <--- TTL в секундах
            'default_base_currency': 'USD',
            'log_level': 'INFO',
            # Add more settings here
        }
        self._load_from_file()

    def _load_from_file(self):
        """Попытка загрузить настройки из config.json или pyproject.toml"""
        config_file = os.path.join(BASE_DIR, "config.json")

        # Пытаемся загрузить из config.json (приоритет)
        if os.path.exists(config_file):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    file_settings = json.load(f)
                    self._settings.update(file_settings)
                    return
            except (FileNotFoundError, json.JSONDecodeError):
                pass

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу"""
        return self._settings.get(key, default)

    def reload(self):
        """Перезагружает настройки из файла"""
        self._load_settings()


settings_loader = SettingsLoader()

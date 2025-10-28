# valutatrade_hub/parser_service/config.py
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass
class ParserConfig:
    # Singleton
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        # Ключ загружается из переменной окружения
        self.EXCHANGERATE_API_KEY: str = os.getenv("a12942fd486ee1b1fed55a13", "a12942fd486ee1b1fed55a13")

        # Эндпоинты
        self.COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
        self.EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

        # Списки валют
        self.BASE_FIAT_CURRENCY: str = "USD"
        self.FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB", "AED", "JPY")
        self.CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
        self.CRYPTO_ID_MAP: dict = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }

        # Пути
        self.RATES_FILE_PATH: str = os.path.join(BASE_DIR, "data", "rates.json")
        self.HISTORY_FILE_PATH: str = os.path.join(BASE_DIR, "data", "exchange_rates.json")

        # Сетевые параметры
        self.REQUEST_TIMEOUT: int = 10


# Создаем экземпляр синглтона
parser_config = ParserConfig()

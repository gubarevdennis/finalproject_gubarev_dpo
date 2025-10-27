# valutatrade_hub/core/utils.py
import json
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal

from .exceptions import CurrencyNotFoundError # Импорт для возможных исключений
from ..infra.database import database_manager

#BASE_DIR = Path(__file__).resolve().parent.parent.parent # теперь не нужно

class RateManager:
    def __init__(self):
        # Заглушка курсов. В реальном приложении они будут подгружаться.
        self.mock_exchange_rates = {
            "USD_USD": Decimal("1.0000"),
            "EUR_USD": Decimal("1.0786"),
            "USD_EUR": Decimal("0.9271"), # Обратный курс
            "BTC_USD": Decimal("59337.21"),
            "USD_BTC": Decimal("0.00001685"), # Обратный курс
            "ETH_USD": Decimal("3720.00"),
            "USD_ETH": Decimal("0.0002688"), # Обратный курс
            "BTC_EUR": Decimal("55000.00"), # Примерный курс
            "EUR_BTC": Decimal("0.00001818") # Примерный обратный курс
        }
        self.rate_ttl_seconds = 300 # Время жизни кеша в секундах

    def get_rates(self):
        rates_data = database_manager.get_rates()
        
        # Если данных нет или они устарели, обновляем
        last_refresh_str = rates_data.get("last_refresh")
        if not last_refresh_str:
            self.refresh_rates()
            rates_data = database_manager.get_rates()
        else:
            try:
                last_refresh = datetime.fromisoformat(last_refresh_str)
                if (datetime.utcnow() - last_refresh).total_seconds() > self.rate_ttl_seconds:
                    self.refresh_rates()
                    rates_data = database_manager.get_rates()
            except ValueError: # Если формат даты некорректен
                self.refresh_rates()
                rates_data = database_manager.get_rates()
                
        return rates_data

    def refresh_rates(self):
        """Обновляет заглушку курсов и сохраняет в rates.json."""
        rates_data = {
            "source": "MockParserService",
            "last_refresh": datetime.utcnow().isoformat(),
            "rates": {}
        }
        
        # Добавляем прямые и обратные курсы
        for pair, rate in self.mock_exchange_rates.items():
            from_currency, to_currency = pair.split('_')
            # Добавляем только если нужная валюта существует в реестре
            # (Это упрощение, в реальном парсере нужно было бы проверять наличие валют)
            rates_data["rates"][pair] = {"rate": str(rate), "updated_at": rates_data["last_refresh"]}

        database_manager.save_rates(rates_data)
        return rates_data

#data_manager = DataManager() # Убрали создание экземпляра DataManager
rate_manager = RateManager() # Передаем в RateManager экземпляр Singleton

# Создадим экземпляр RateManager при старте приложения:
rate_manager = RateManager()
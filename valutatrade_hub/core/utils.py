# valutatrade_hub/core/utils.py
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

from .currencies import CurrencyNotFoundError # Импорт для возможных исключений
#from .models import get_currency # Не нужно здесь

BASE_DIR = Path(__file__).resolve().parent.parent.parent

USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
PORTFOLIOS_FILE = os.path.join(BASE_DIR, "data", "portfolios.json")
RATES_FILE = os.path.join(BASE_DIR, "data", "rates.json")

class DataManager:
    def __init__(self):
        self.users_file = USERS_FILE
        self.portfolios_file = PORTFOLIOS_FILE
        self.rates_file = RATES_FILE

    def _load_json(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content:
                    return json.loads(content)
                else:
                    return {} # Возвращаем пустой словарь, если файл пустой
        except FileNotFoundError:
            return {} # Возвращаем пустой словарь, если файл не найден
        except json.JSONDecodeError:
            return {} # Возвращаем пустой словарь при ошибке парсинга

    def _save_json(self, data, file_path):
        def default(obj):
            if isinstance(obj, Decimal):
                return str(obj)
            raise TypeError
            
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, default=default)

    def get_all_users(self):
        return self.load_or_default(self.users_file, [])

    def save_users(self, users):
        self._save_json(users, self.users_file)

    def get_user_by_username(self, username):
        users = self.get_all_users()
        for user in users:
            if user.get('username') == username:
                return user
        return None

    def get_all_portfolios(self):
        return self.load_or_default(self.portfolios_file, [])

    def save_portfolios(self, portfolios):
        self._save_json(portfolios, self.portfolios_file)

    def get_portfolio_by_user_id(self, user_id):
        portfolios = self.get_all_portfolios()
        for portfolio in portfolios:
            if portfolio.get('user_id') == user_id:
                return portfolio
        return None

    def get_rates(self):
        # Возвращаем rates, гарантируя, что это словарь, даже если файл пуст или ошибка
        return self.load_or_default(self.rates_file, {"rates": {}, "last_refresh": None, "source": "Unknown"})

    def save_rates(self, rates):
        self._save_json(rates, self.rates_file)

    def load_or_default(self, file_path, default_value):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content:
                    return json.loads(content)
                else:
                    return default_value
        except FileNotFoundError:
            return default_value
        except json.JSONDecodeError:
            return default_value


class RateManager:
    def __init__(self, data_manager=DataManager()):
        self.data_manager = data_manager
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
        rates_data = self.data_manager.get_rates()
        
        # Если данных нет или они устарели, обновляем
        last_refresh_str = rates_data.get("last_refresh")
        if not last_refresh_str:
            self.refresh_rates()
            rates_data = self.data_manager.get_rates()
        else:
            try:
                last_refresh = datetime.fromisoformat(last_refresh_str)
                if (datetime.utcnow() - last_refresh).total_seconds() > self.rate_ttl_seconds:
                    self.refresh_rates()
                    rates_data = self.data_manager.get_rates()
            except ValueError: # Если формат даты некорректен
                self.refresh_rates()
                rates_data = self.data_manager.get_rates()
                
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

        self.data_manager.save_rates(rates_data)
        return rates_data

data_manager = DataManager()
rate_manager = RateManager(data_manager)
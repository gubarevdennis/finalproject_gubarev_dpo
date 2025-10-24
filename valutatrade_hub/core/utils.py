# valutatrade_hub/core/utils.py
import json
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal

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
                    return json.loads(content)  # УБРАЛ parse_float=Decimal
                else:
                    return []
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []

    def _save_json(self, data, file_path):
        def default(obj):
            if isinstance(obj, Decimal):
                return str(obj)
            raise TypeError
            
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, default=default)

    def get_all_users(self):
        return self._load_json(self.users_file)

    def save_users(self, users):
        self._save_json(users, self.users_file)

    def get_user_by_username(self, username):
        users = self.get_all_users()
        for user in users:
            if user['username'] == username:
                return user
        return None

    def get_all_portfolios(self):
        return self._load_json(self.portfolios_file)

    def save_portfolios(self, portfolios):
        self._save_json(portfolios, self.portfolios_file)

    def get_portfolio_by_user_id(self, user_id):
        portfolios = self.get_all_portfolios()
        for portfolio in portfolios:
            if portfolio['user_id'] == user_id:
                return portfolio
        return None

    def get_rates(self):
        rates = self._load_json(self.rates_file)
        return rates # Возвращаем rates (убедимся, что есть ключ 'rates')

    def save_rates(self, rates):
        self._save_json(rates, self.rates_file)

class RateManager:
    def __init__(self, data_manager=DataManager()):
        self.data_manager = data_manager
        # Гарантируем наличие всех необходимых курсов для конвертации в USD
        self.exchange_rates = {
            "BTC_USD": {"rate": Decimal("59337.21"), "updated_at": "2025-10-09T10:29:42"},
            "ETH_USD": {"rate": Decimal("3720.00"), "updated_at": "2025-10-09T10:35:00"},
            "EUR_USD": {"rate": Decimal("1.0786"), "updated_at": "2025-10-09T10:30:00"},
            "USD_USD": {"rate": Decimal("1.0000"), "updated_at": "2025-10-09T10:30:00"},
            "RUB_USD": {"rate": Decimal("0.01016"), "updated_at": "2025-10-09T10:31:12"},
        }

    def get_rates(self):
        rates = self.data_manager.get_rates()
        if not rates or 'rates' not in rates:  # Проверяем, что rates и 'rates' существуют
            self.refresh_rates()
            rates = self.data_manager.get_rates()
        return rates

    def refresh_rates(self):
        rates_data = {"source": "MockParserService", "last_refresh": datetime.utcnow().isoformat(), "rates": {}}
        for currency_pair, data in self.exchange_rates.items():
            rates_data["rates"][currency_pair] = {"rate": str(data['rate']), "updated_at": data['updated_at']}
        self.data_manager.save_rates(rates_data)
        return rates_data

data_manager = DataManager()
rate_manager = RateManager(data_manager)
# valutatrade_hub/infra/database.py
import json
import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class DatabaseManager:
    """
    Singleton для управления JSON-хранилищем данных.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Инициализация путей к файлам и загрузка данных."""
        self.users_file = os.path.join(BASE_DIR, "data", "users.json")
        self.portfolios_file = os.path.join(BASE_DIR, "data", "portfolios.json")
        self.rates_file = os.path.join(BASE_DIR, "data", "rates.json")
        # Новый файл, который будет использовать Parser Service
        self.exchange_rates_history_file = os.path.join(BASE_DIR, "data", "exchange_rates.json")

    def _load_json(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content:
                    return json.loads(content)
                else:
                    return {}
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}

    def _save_json(self, data, file_path):
        def default(obj):
            if isinstance(obj, Decimal):
                return str(obj)
            raise TypeError

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, default=default)

    # --- Методы для Core Service (пока используют те же названия, что и раньше) ---
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
        return self.load_or_default(self.rates_file, {"pairs": {}, "last_refresh": None})

    def save_rates(self, rates):
        self._save_json(rates, self.rates_file)

    # --- Новые методы для Parser Service ---
    def get_exchange_rates_history(self):
        return self.load_or_default(self.exchange_rates_history_file, {})

    def save_exchange_rates_history(self, history_data):
        self._save_json(history_data, self.exchange_rates_history_file)

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


database_manager = DatabaseManager()

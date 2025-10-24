# valutatrade_hub/core/models.py
import hashlib
import secrets
from datetime import datetime

class ValidationError(Exception):
    pass

class User:
    def __init__(self, user_id: int, username: str, hashed_password: str, salt: str, registration_date: str):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str):
        if not value:
            raise ValidationError("Имя пользователя не может быть пустым.")
        self._username = value

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    @property
    def salt(self) -> str:
        return self._salt

    @property
    def registration_date(self) -> str:
        return self._registration_date

    def get_user_info(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date
        }

    def change_password(self, new_password: str):
        if len(new_password) < 4:
            raise ValidationError("Пароль должен быть не короче 4 символов.")
        self._hashed_password = hashlib.sha256((new_password + self._salt).encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        hashed_password = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return hashed_password == self._hashed_password

    @classmethod
    def create_new(cls, user_id: int, username: str, password: str):
        if len(password) < 4:
            raise ValidationError("Пароль должен быть не короче 4 символов.")
        salt = secrets.token_hex(8)
        hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
        registration_date = datetime.utcnow().isoformat()
        return cls(user_id, username, hashed_password, salt, registration_date)


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self.currency_code = currency_code
        self._balance = balance

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, amount: float):
        if not isinstance(amount, (int, float)):
            raise ValidationError("Баланс должен быть числом.")
        if amount < 0:
            raise ValidationError("Баланс не может быть отрицательным.")
        self._balance = float(amount)

    def deposit(self, amount: float):
        if amount <= 0:
            raise ValidationError("Сумма пополнения должна быть положительной.")
        self._balance += amount

    def withdraw(self, amount: float):
        if amount <= 0:
            raise ValidationError("Сумма снятия должна быть положительной.")
        if amount > self._balance:
            raise ValidationError(f"Недостаточно средств. Доступно: {self._balance}, Требуется: {amount}")
        self._balance -= amount

    def get_balance_info(self) -> dict:
        return {
            "currency_code": self.currency_code,
            "balance": self._balance
        }


class Portfolio:
    def __init__(self, user_id: int, wallets: dict[str, Wallet] = None):
        self._user_id = user_id
        self._wallets = wallets if wallets is not None else {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        return self._wallets.copy()  # Return a copy to prevent direct modification

    def add_currency(self, currency_code: str):
        if currency_code in self._wallets:
            raise ValidationError(f"Валюта {currency_code} уже есть в портфеле.")
        self._wallets[currency_code] = Wallet(currency_code)

    def get_total_value(self, base_currency='USD', exchange_rates=None):
        total_value = 0.0
        if exchange_rates is None:
            exchange_rates = {}
        for currency_code, wallet in self._wallets.items():
            if currency_code == base_currency:
                total_value += wallet.balance
            elif f"{currency_code}_{base_currency}" in exchange_rates:
                rate = exchange_rates[f"{currency_code}_{base_currency}"]
                total_value += wallet.balance * rate
        return total_value

    def get_wallet(self, currency_code: str) -> Wallet:
        if currency_code not in self._wallets:
            raise ValidationError(f"Валюта {currency_code} не найдена в портфеле.")
        return self._wallets[currency_code]
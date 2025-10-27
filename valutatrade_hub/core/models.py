# valutatrade_hub/core/models.py
import re
from decimal import Decimal

from .exceptions import InsufficientFundsError, ValidationError, CurrencyNotFoundError
from .currencies import get_currency  # Correct import for get_currency

class Currency:
    """Абстрактный базовый класс для всех валют."""

    def __init__(self, name: str, code: str):
        self._validate_code(code)
        self._validate_name(name)
        self._name = name
        self._code = code

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._validate_name(value)
        self._name = value

    @property
    def code(self) -> str:
        return self._code

    @code.setter
    def code(self, value: str):
        self._validate_code(value)
        self._code = value

    def _validate_code(self, code: str):
        if not re.fullmatch(r"^[A-Z]{2,5}$", code):
            raise ValidationError(
                f"Код валюты '{code}' должен быть в верхнем регистре, от 2 до 5 символов и без пробелов."
            )

    def _validate_name(self, name: str):
        if not name or not name.strip():
            raise ValidationError("Имя валюты не может быть пустым.")

    def get_display_info(self) -> str:
        """Возвращает строковое представление валюты для UI/логов."""
        return f"[{self.__class__.__name__.upper()}] {self.code} - {self.name}"

    def __str__(self):
        return self.get_display_info()

    def __repr__(self):
        return f"{self.__class__.__name__}(code='{self.code}', name='{self.name}')"


class FiatCurrency(Currency):
    """Класс для фиатных валют."""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self._validate_issuing_country(issuing_country)
        self._issuing_country = issuing_country

    @property
    def issuing_country(self) -> str:
        return self._issuing_country

    @issuing_country.setter
    def issuing_country(self, value: str):
        self._validate_issuing_country(value)
        self._issuing_country = value

    def _validate_issuing_country(self, value: str):
        if not value or not value.strip():
            raise ValidationError("Страна-эмитент не может быть пустой.")

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Класс для криптовалют."""

    def __init__(self, name: str, code: str, algorithm: str, market_cap: Decimal):
        super().__init__(name, code)
        self._validate_algorithm(algorithm)
        self._validate_market_cap(market_cap)
        self._algorithm = algorithm
        self._market_cap = market_cap

    @property
    def algorithm(self) -> str:
        return self._algorithm

    @algorithm.setter
    def algorithm(self, value: str):
        self._validate_algorithm(value)
        self._algorithm = value

    @property
    def market_cap(self) -> Decimal:
        return self._market_cap

    @market_cap.setter
    def market_cap(self, value: Decimal):
        self._validate_market_cap(value)
        self._market_cap = value

    def _validate_algorithm(self, value: str):
        if not value or not value.strip():
            raise ValidationError("Алгоритм не может быть пустым.")

    def _validate_market_cap(self, value: Decimal):
        if not isinstance(value, Decimal) or value < 0:
            raise ValidationError("Рыночная капитализация должна быть положительным числом Decimal.")

    def get_display_info(self) -> str:
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"


# --- User Class (из предыдущей версии) ---
class User:
    """Пользователь системы."""

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

    def get_user_info(self) -> str:
        return f"User ID: {self._user_id}, Username: {self._username}, Registration Date: {self._registration_date}"

    def change_password(self, new_password: str):
        if len(new_password) < 4:
            raise ValidationError("Пароль должен быть не короче 4 символов.")
        # Здесь должна быть логика с хешированием нового пароля
        self._hashed_password = new_password  # Замените на реальное хеширование с солью

    def verify_password(self, password: str) -> bool:
        # Здесь должна быть логика сравнения с хешем
        return password == self._hashed_password  # Замените на реальное сравнение с хешем


# --- Wallet Class ---
class Wallet:
    """Кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: Decimal = Decimal("0.0")):
        # ВАЖНО: Валидация currency_code теперь через get_currency из currencies.py
        try:
            get_currency(currency_code)  # Проверка существования валюты
        except CurrencyNotFoundError as e:
            raise ValidationError(f"Недопустимый код валюты: {e}") from e

        self.currency_code = currency_code
        if not isinstance(balance, Decimal):
            balance = Decimal(balance)
        self._balance = balance  # Изначально присваиваем, setter выполнит валидацию

    @property
    def balance(self) -> Decimal:
        return self._balance

    @balance.setter
    def balance(self, value: Decimal):
        if not isinstance(value, Decimal):
            raise ValidationError("Баланс должен быть числом Decimal.")
        if value < 0:
            raise ValidationError("Баланс не может быть отрицательным.")
        self._balance = value

    def deposit(self, amount: Decimal):
        """Пополнение баланса."""
        if not isinstance(amount, Decimal) or amount <= 0:
            raise ValidationError("Сумма пополнения должна быть положительным числом Decimal.")
        self.balance += amount

    def withdraw(self, amount: Decimal):
        """Снятие средств (если баланс позволяет)."""
        if not isinstance(amount, Decimal) or amount <= 0:
            raise ValidationError("Сумма снятия должна быть положительным числом Decimal.")
        if amount > self.balance:
            raise InsufficientFundsError(
                message=f"Недостаточно средств: доступно {self.balance} {self.currency_code}, требуется {amount} {self.currency_code}",
                available_amount=self.balance,
                required_amount=amount,
                currency_code=self.currency_code
            )
        self.balance -= amount

    def get_balance_info(self) -> str:
        return f"Баланс: {self.balance} {self.currency_code}"


# --- Portfolio Class ---
class Portfolio:
    """Управление всеми кошельками одного пользователя."""

    def __init__(self, user_id: int, wallets: dict[str, Wallet] = None):
        self._user_id = user_id
        self._wallets = wallets if wallets is not None else {}

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def wallets(self) -> dict[str, Wallet]:
        return self._wallets.copy()

    def add_currency(self, currency_code: str):
        """Добавляет новый кошелёк в портфель (если его ещё нет)."""
        currency_code = currency_code.upper()
        try:
            get_currency(currency_code)  # Проверка существования валюты
        except CurrencyNotFoundError as e:
            raise ValidationError(f"Недопустимый код валюты: {e}") from e

        if currency_code in self._wallets:
            raise ValidationError(f"Кошелек для валюты '{currency_code}' уже существует.")

        self._wallets[currency_code] = Wallet(currency_code=currency_code)

    def get_total_value(self, base_currency='USD', exchange_rates=None) -> Decimal:
        """Возвращает общую стоимость всех валют пользователя в указанной базовой валюте."""
        total_value = Decimal('0.0')
        if exchange_rates is None:
            exchange_rates = {}  # Заглушка

        try:
            get_currency(base_currency)
        except CurrencyNotFoundError as e:
            raise ValidationError(f"Неизвестная базовая валюта '{base_currency}'.") from e

        for currency_code, wallet in self._wallets.items():
            balance = wallet.balance
            if currency_code == base_currency:
                total_value += balance
            else:
                rate_key = f"{currency_code}_{base_currency}"

                # Важно: Проверяем наличие курса в 'rates' и сам курс
                rate_info = exchange_rates.get('pairs', {}).get(rate_key)

                # Важно: Если rate_info нет, попробуем перевернуть пару валют (base->currency)
                if not rate_info and base_currency != 'USD':
                    rate_key_reversed = f"{base_currency}_{currency_code}"
                    rate_info = exchange_rates.get('pairs', {}).get(rate_key_reversed)
                    if rate_info and 'rate' in rate_info:
                        try:
                            rate_value = Decimal('1.0') / Decimal(rate_info['rate'])
                            total_value += balance * rate_value
                            continue  # <--- Важно: переходим к следующей валюте
                        except (ValueError, TypeError, ZeroDivisionError):
                            pass  # Обработка ошибки (лог или что-то еще)
                if rate_info and 'rate' in rate_info:
                    try:
                        rate_value = Decimal(rate_info['rate'])
                        total_value += balance * rate_value
                    except (ValueError, TypeError):
                        # Игнорируем ошибки конвертации для отдельной валюты
                        pass
        return total_value

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает объект Wallet по коду валюты."""
        currency_code = currency_code.upper()
        if currency_code not in self._wallets:
            raise CurrencyNotFoundError(f"Кошелек для валюты '{currency_code}' не найден в портфеле.", code=currency_code)
        return self._wallets[currency_code]
# valutatrade_hub/core/currencies.py
import re
from decimal import Decimal
from abc import ABC, abstractmethod

from .exceptions import CurrencyNotFoundError, ValidationError

class Currency(ABC):
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


# --- Реестр валют (фабрика) ---
_currency_registry = {
    "USD": FiatCurrency(name="US Dollar", code="USD", issuing_country="United States"),
    "EUR": FiatCurrency(name="Euro", code="EUR", issuing_country="Eurozone"),
    "RUB": FiatCurrency(name="Russian Ruble", code="RUB", issuing_country="Russian Federation"),
    "BTC": CryptoCurrency(name="Bitcoin", code="BTC", algorithm="SHA-256", market_cap=Decimal("1120000000000")),
    "ETH": CryptoCurrency(name="Ethereum", code="ETH", algorithm="Ethash", market_cap=Decimal("450000000000")),
}

def get_currency(code: str) -> Currency:
    """Возвращает объект Currency по его коду."""
    code = code.upper()
    currency = _currency_registry.get(code)
    if not currency:
        raise CurrencyNotFoundError(f"Неизвестная валюта '{code}'", code=code)
    return currency
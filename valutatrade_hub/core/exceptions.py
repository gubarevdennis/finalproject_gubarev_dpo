# valutatrade_hub/core/exceptions.py

class ValidationError(Exception):
    """Базовое исключение для ошибок валидации входных данных."""
    pass

class UserNotFoundError(Exception):
    """Исключение, когда пользователь не найден."""
    pass

class InvalidCredentialsError(Exception):
    """Исключение для неверных учетных данных."""
    pass

class InsufficientFundsError(Exception):
    """Исключение, когда недостаточно средств для операции."""
    def __init__(self, message, available_amount, required_amount, currency_code):
        super().__init__(message)
        self.available_amount = available_amount
        self.required_amount = required_amount
        self.currency_code = currency_code

class CurrencyNotFoundError(Exception):
    """Исключение, когда запрошенная валюта не найдена."""
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code

class ApiRequestError(Exception):
    """Исключение для сбоев при обращении к внешнему API."""
    def __init__(self, message, reason=None):
        super().__init__(message)
        self.reason = reason

# Дополнительные исключения, если потребуются в будущем
class PortfolioError(Exception):
    """Базовое исключение для ошибок портфеля."""
    pass
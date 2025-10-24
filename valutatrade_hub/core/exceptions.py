# valutatrade_hub/core/exceptions.py
from .models import ValidationError

class InsufficientFundsError(Exception):
    """Raised when trying to withdraw more than available balance."""
    pass

class CurrencyNotFoundError(Exception):
    """Raised when a specified currency wallet does not exist."""
    pass

class UserNotFoundError(Exception):
    """Raised when a user cannot be found."""
    pass

class InvalidCredentialsError(Exception):
    """Raised when username/password combination is incorrect."""
    pass

class ApiRequestError(Exception):
    """Raised for issues connecting to external APIs."""
    pass

# (Уже должно быть в файле, но дополним для полноты)
class PortfolioNotFoundError(Exception):
    """Raised when a user portfolio is missing."""
    pass

class TtlExpiredError(Exception):
    """Raised when rate data is too old (TTL exceeded)."""
    pass
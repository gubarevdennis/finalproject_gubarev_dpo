# valutatrade_hub/core/usecases.py
import hashlib
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from ..decorators import log_action
from ..infra.database import database_manager
from ..infra.settings import settings_loader
from .exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    InvalidCredentialsError,
    UserNotFoundError,
    ValidationError,
)
from .models import get_currency

BASE_CURRENCY = settings_loader.get('default_base_currency', 'USD')
RATE_TTL_SECONDS = settings_loader.get('rates_ttl_seconds', 300)  # Используем настройку TTL


def generate_user_id(users):
    """Генерирует новый user_id"""
    return max((user['user_id'] for user in users), default=0) + 1


@log_action()
def register_user(username, password):
    """Регистрирует нового пользователя."""
    if not username or not password:
        raise ValidationError("Имя пользователя и пароль обязательны.")
    if len(password) < 4:
        raise ValidationError("Пароль должен быть не короче 4 символов.")

    existing_user = database_manager.get_user_by_username(username)
    if existing_user:
        raise UserNotFoundError(f"Имя пользователя '{username}' уже занято.")

    # Явно преобразуем в список
    users = list(database_manager.get_all_users())

    user_id = generate_user_id(users)
    salt = secrets.token_hex(8)
    hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
    registration_date = datetime.utcnow().isoformat()

    new_user = {
        "user_id": user_id,
        "username": username,
        "hashed_password": hashed_password,
        "salt": salt,
        "registration_date": registration_date
    }
    users.append(new_user)
    database_manager.save_users(users)

    # Создаем портфель с начальным балансом в USD
    initial_usd_balance = Decimal("1000.00")
    new_portfolio = {"user_id": user_id, "wallets": {BASE_CURRENCY: {'balance': str(initial_usd_balance)}}}

    portfolios = database_manager.get_all_portfolios()
    portfolios.append(new_portfolio)
    database_manager.save_portfolios(portfolios)

    return user_id


@log_action()
def login_user(username, password):
    """Проверяет имя пользователя и пароль"""
    user = database_manager.get_user_by_username(username)
    if not user:
        raise UserNotFoundError(f"Пользователь '{username}' не найден")

    salt = user['salt']
    test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    if test_hash != user['hashed_password']:
        raise InvalidCredentialsError("Неверный пароль")

    return user['user_id']


def show_portfolio(user_id, base_currency=BASE_CURRENCY):
    """Отображает портфель пользователя"""
    try:
        get_currency(base_currency)
    except CurrencyNotFoundError as e:
        raise ValidationError(f"Неизвестная базовая валюта '{base_currency}'.") from e

    portfolio_raw = database_manager.get_portfolio_by_user_id(user_id)
    if not portfolio_raw:
        raise UserNotFoundError(f"Портфель для пользователя с ID {user_id} не найден.")

    rates_cache = database_manager.get_rates()

    total_value = Decimal('0.0')
    portfolio_info = {}

    wallets = portfolio_raw.get('wallets', {})
    if wallets:
        for curr, data in wallets.items():
            balance = data.get('balance', 0)
            if not isinstance(balance, Decimal):
                balance = Decimal(str(balance))

            value = Decimal('0.0')
            if curr == base_currency:
                value = balance
            else:
                rate_key = f"{curr}_{base_currency}"
                rate_info = rates_cache.get('pairs', {}).get(rate_key)
                if rate_info:
                    if is_rate_fresh(rate_info):
                        try:
                            rate_value = Decimal(rate_info['rate'])
                            value = balance * rate_value
                        except (ValueError, TypeError):
                            value = Decimal('0.0')
                    else:
                        value = Decimal('0.0')  # Курс устарел
                else:
                    value = Decimal('0.0')  # Курс отсутствует

            total_value += value
            portfolio_info[curr] = {"balance": balance, "value_in_base": value}

    return portfolio_info, total_value


@log_action(verbose=True)
def buy_currency(user_id, currency, amount):
    """Покупка валюты."""
    currency = currency.upper()

    if amount <= 0:
        raise ValidationError("'amount' должен быть положительным числом")

    try:
        get_currency(currency)
    except CurrencyNotFoundError as e:
        raise e

    portfolio_raw = database_manager.get_portfolio_by_user_id(user_id)
    if not portfolio_raw:
        raise UserNotFoundError("Портфель не найден.")

    rates = database_manager.get_rates()
    rate_key = f"{currency}_{BASE_CURRENCY}"

    rate_info = rates.get('pairs', {}).get(rate_key)

    # Сначала проверяем, есть ли курс вообще
    if not rate_info:
        raise ApiRequestError(f"Курс {currency}→{BASE_CURRENCY} недоступен.")

    # Потом проверяем, не устарел ли он
    if not is_rate_fresh(rate_info):
        raise ApiRequestError(f"Курс {currency}→{BASE_CURRENCY} устарел. Обновите курсы.")

    rate = Decimal(rate_info['rate'])
    amount_dec = Decimal(str(amount))
    cost = amount_dec * rate

    # Автоматическое создание кошелька, если его нет
    if 'wallets' not in portfolio_raw:
        portfolio_raw['wallets'] = {}
    if currency not in portfolio_raw['wallets']:
        portfolio_raw['wallets'][currency] = {'balance': '0.0'}
    if BASE_CURRENCY not in portfolio_raw['wallets']:
        portfolio_raw['wallets'][BASE_CURRENCY] = {'balance': '0.0'}

    usd_balance = Decimal(str(portfolio_raw['wallets'][BASE_CURRENCY]['balance']))
    if usd_balance < cost:
        raise InsufficientFundsError(
            message=f"Недостаточно {BASE_CURRENCY} для совершения покупки.",
            available_amount=usd_balance,
            required_amount=cost,
            currency_code=BASE_CURRENCY
        )

    portfolio_raw['wallets'][BASE_CURRENCY]['balance'] = str(usd_balance - cost)
    currency_balance = Decimal(str(portfolio_raw['wallets'][currency]['balance']))
    portfolio_raw['wallets'][currency]['balance'] = str(currency_balance + amount_dec)

    # Обновляем портфель в базе данных
    portfolios = database_manager.get_all_portfolios()
    for i, p in enumerate(portfolios):
        if p['user_id'] == user_id:
            portfolios[i] = portfolio_raw
            break
    database_manager.save_portfolios(portfolios)

    return f"Покупка выполнена: {amount_dec:.4f} {currency} по курсу {rate:.2f} {BASE_CURRENCY}/{currency}"


@log_action(verbose=True)
def sell_currency(user_id, currency, amount):
    """Продажа валюты."""
    currency = currency.upper()

    if amount <= 0:
        raise ValidationError("'amount' должен быть положительным числом")

    try:
        get_currency(currency)
    except CurrencyNotFoundError as e:
        raise e

    portfolio_raw = database_manager.get_portfolio_by_user_id(user_id)
    if not portfolio_raw:
        raise UserNotFoundError("Портфель не найден.")

    if 'wallets' not in portfolio_raw or currency not in portfolio_raw['wallets']:
        raise CurrencyNotFoundError(f"У вас нет кошелька '{currency}'. "
                                    f"Добавьте валюту: она создается автоматически при первой покупке.",
                                    code=currency)

    currency_balance = Decimal(str(portfolio_raw['wallets'][currency]['balance']))
    if currency_balance < amount:
        raise InsufficientFundsError(
            message=f"Недостаточно средств: доступно {currency_balance:.4f} {currency}, "
                    f"требуется {amount:.4f} {currency}",
            available_amount=currency_balance,
            required_amount=amount,
            currency_code=currency
        )

    rates = database_manager.get_rates()
    rate_key = f"{currency}_{BASE_CURRENCY}"

    rate_info = rates.get('pairs', {}).get(rate_key)
    if not rate_info:
        raise ApiRequestError(f"Курс {currency}→{BASE_CURRENCY} недоступен.")

    if not is_rate_fresh(rate_info):
        raise ApiRequestError(f"Курс {currency}→{BASE_CURRENCY} устарел. Обновите курсы.")

    rate = Decimal(rate_info['rate'])
    amount_dec = Decimal(str(amount))
    revenue = amount_dec * rate

    portfolio_raw['wallets'][currency]['balance'] = str(currency_balance - amount_dec)

    if BASE_CURRENCY not in portfolio_raw['wallets']:
        portfolio_raw['wallets'][BASE_CURRENCY] = {'balance': '0.0'}

    usd_balance = Decimal(str(portfolio_raw['wallets'][BASE_CURRENCY]['balance']))
    portfolio_raw['wallets'][BASE_CURRENCY]['balance'] = str(usd_balance + revenue)

    # Обновляем портфель в базе данных
    portfolios = database_manager.get_all_portfolios()
    for i, p in enumerate(portfolios):
        if p['user_id'] == user_id:
            portfolios[i] = portfolio_raw
            break
    database_manager.save_portfolios(portfolios)

    return f"Продажа выполнена: {amount_dec:.4f} {currency} по курсу {rate:.2f} {BASE_CURRENCY}/{currency}"


def get_rate(from_currency, to_currency):
    """Получает курс обмена валют."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    try:
        get_currency(from_currency)
        get_currency(to_currency)
    except CurrencyNotFoundError as e:
        raise e

    rates_data_from_manager = database_manager.get_rates()
    rate_key = f"{from_currency}_{to_currency}"

    rate_info = rates_data_from_manager.get('pairs', {}).get(rate_key)

    if not rate_info:
        raise ApiRequestError("Данные о курсе недоступны.")

    if not is_rate_fresh(rate_info):
        raise ApiRequestError("Данные о курсе устарели. Выполните 'update-rates'.")

    rate_value = Decimal(rate_info['rate'])
    return f"Курс {from_currency}→{to_currency}: {rate_value:.8f} (обновлено: {rate_info['updated_at'][:19]})"


def is_rate_fresh(rate_info):
    """Проверяет, не устарел ли курс."""
    if not rate_info or 'updated_at' not in rate_info:
        return False

    updated_at_str = rate_info['updated_at']
    updated_at_dt = datetime.fromisoformat(updated_at_str)
    return (datetime.utcnow() - updated_at_dt) <= timedelta(seconds=RATE_TTL_SECONDS)

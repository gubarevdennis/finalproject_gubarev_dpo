# valutatrade_hub/core/usecases.py
import hashlib
import secrets
from datetime import datetime
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
from .models import get_currency  # Correct import for get_currency
from .utils import rate_manager

BASE_CURRENCY = settings_loader.get('default_base_currency', 'USD')
RATE_TTL_SECONDS = settings_loader.get('rates_ttl_seconds', 300)


def generate_user_id(users):
    return max((user['user_id'] for user in users), default=0) + 1


@log_action()
def register_user(username, password):
    if not username or not password:
        raise ValidationError("Имя пользователя и пароль обязательны.")
    if len(password) < 4:
        raise ValidationError("Пароль должен быть не короче 4 символов.")

    if database_manager.get_user_by_username(username):
        raise UserNotFoundError(f"Имя пользователя '{username}' уже занято.")

    user_id = generate_user_id(database_manager.get_all_users())
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
    users = database_manager.get_all_users()
    users.append(new_user)
    database_manager.save_users(users)

    initial_usd_balance = Decimal("1000.00")
    new_portfolio = {"user_id": user_id, "wallets": {BASE_CURRENCY: {'balance': str(initial_usd_balance)}}}

    portfolios = database_manager.get_all_portfolios()
    portfolios.append(new_portfolio)
    database_manager.save_portfolios(portfolios)

    return user_id


@log_action()
def login_user(username, password):
    users = database_manager.get_user_by_username(username)
    if not users:
        raise UserNotFoundError(f"Пользователь '{username}' не найден")

    salt = users['salt']
    test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    if test_hash != users['hashed_password']:
        raise InvalidCredentialsError("Неверный пароль")

    return users['user_id']


def show_portfolio(user_id, base_currency=BASE_CURRENCY):
    try:
        get_currency(base_currency)
    except CurrencyNotFoundError as e:
        raise ValidationError(f"Неизвестная базовая валюта '{base_currency}'.") from e

    portfolio_raw = database_manager.get_portfolio_by_user_id(user_id)
    rates_cache = rate_manager.get_rates()

    if not portfolio_raw:
        raise UserNotFoundError(f"Портфель для пользователя с ID {user_id} не найден.")

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

                # Проверяем наличие 'rates' и самого курса
                if ('pairs' in rates_cache and rate_key in rates_cache['pairs']
                            and 'rate' in rates_cache['pairs'][rate_key]):
                    try:
                        rate_value = Decimal(rates_cache['pairs'][rate_key]['rate'])
                        value = balance * rate_value
                    except (ValueError, TypeError):
                        value = Decimal('0.0')
                else:
                    # Если нужного курса нет (например, BTC_EUR), оставляем value = 0.0
                    value = Decimal('0.0')

            total_value += value
            portfolio_info[curr] = {"balance": balance, "value_in_base": value}

    return portfolio_info, total_value


@log_action(verbose=True)  # Добавляем декоратор
def buy_currency(user_id, currency, amount):
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

    rates = rate_manager.get_rates()
    rate_key = f"{currency}_{BASE_CURRENCY}"

    if 'pairs' not in rates or rate_key not in rates['pairs'] or 'rate' not in rates['pairs'][rate_key]:
        raise ApiRequestError(f"Курс {currency}→{BASE_CURRENCY} недоступен.")

    rate = Decimal(rates['pairs'][rate_key]['rate'])
    amount_dec = Decimal(str(amount))
    cost = amount_dec * rate

    # Автосоздание кошелька, если его нет
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

    portfolios = database_manager.get_all_portfolios()
    for i, p in enumerate(portfolios):
        if p['user_id'] == user_id:
            portfolio = portfolio_raw
            portfolios[i] = portfolio
            break
    database_manager.save_portfolios(portfolios)

    return f"Покупка выполнена: {amount_dec:.4f} {currency} по курсу {rate:.2f} {BASE_CURRENCY}/{currency}"


@log_action(verbose=True)  # Добавляем декоратор
def sell_currency(user_id, currency, amount):
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

    if currency not in portfolio_raw['wallets']:
        raise CurrencyNotFoundError(f"У вас нет кошелька '{currency}'. "
                + "Добавьте валюту: она создаётся автоматически при первой покупке.", code=currency)

    currency_balance = Decimal(str(portfolio_raw['wallets'][currency]['balance']))

    if currency_balance < amount:
        raise InsufficientFundsError(
            message=f"Недостаточно средств: доступно {currency_balance:.4f} {currency}, " +
                                                f"требуется {amount:.4f} {currency}",
            available_amount=currency_balance,
            required_amount=amount,
            currency_code=currency
        )

    rates = rate_manager.get_rates()
    rate_key = f"{currency}_{BASE_CURRENCY}"

    if ('pairs' not in rates or rate_key not in rates['pairs']
        or 'rate' not in rates['pairs'][rate_key]):
        raise ApiRequestError(f"Курс {currency}→{BASE_CURRENCY} недоступен.")

    rate = Decimal(rates['pairs'][rate_key]['rate'])
    amount_dec = Decimal(str(amount))
    revenue = amount_dec * rate

    portfolio_raw['wallets'][currency]['balance'] = str(currency_balance - amount_dec)

    if BASE_CURRENCY not in portfolio_raw['wallets']:
        portfolio_raw['wallets'][BASE_CURRENCY] = {'balance': '0.0'}

    usd_balance = Decimal(str(portfolio_raw['wallets'][BASE_CURRENCY]['balance']))

    portfolio_raw['wallets'][BASE_CURRENCY]['balance'] = str(usd_balance + revenue)

    portfolios = database_manager.get_all_portfolios()
    for i, p in enumerate(portfolios):
        if p['user_id'] == user_id:
            portfolio = portfolio_raw
            portfolios[i] = portfolio
            break

    database_manager.save_portfolios(portfolios)

    return f"Продажа выполнена: {amount_dec:.4f} {currency} по курсу {rate:.2f} {BASE_CURRENCY}/{currency}"


def get_rate(from_currency, to_currency):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    try:
        get_currency(from_currency)
        get_currency(to_currency)
    except CurrencyNotFoundError as e:
        raise e

    rates_data_from_manager = rate_manager.get_rates()

    rate_key = f"{from_currency}_{to_currency}"

    rate_info = None
    if 'pairs' in rates_data_from_manager and rate_key in rates_data_from_manager['pairs']:
        rate_info = rates_data_from_manager['pairs'][rate_key]

    if rate_info:
        updated_at_str = rate_info.get('updated_at')
        if updated_at_str:
            updated_at_dt = datetime.fromisoformat(updated_at_str)
            if (datetime.utcnow() - updated_at_dt).total_seconds() <= RATE_TTL_SECONDS:
                rate_value = Decimal(rate_info['rate'])
                return f"Курс {from_currency}→{to_currency}: {rate_value:.8f} (обновлено: {updated_at_str[:19]})"

    # Здесь должна быть попытка обновления курсов (через Parser Service)
    # Но пока это не реализовано, мы просто возвращаем "нет данных"
    raise ApiRequestError("Данные о курсе недоступны.")

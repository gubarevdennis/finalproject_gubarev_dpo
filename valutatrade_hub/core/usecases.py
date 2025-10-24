# valutatrade_hub/core/usecases.py
import hashlib
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

from .utils import data_manager, rate_manager

# --- Исключения (для CLI) ---
class UserNotFoundError(Exception): pass
class InvalidCredentialsError(Exception): pass
class InsufficientFundsError(Exception):
    def __init__(self, available, required, currency):
        self.available = available
        self.required = required
        self.currency = currency
        super().__init__(f"Недостаточно средств")

class CurrencyNotFoundError(Exception): pass
class ApiRequestError(Exception): pass

BASE_CURRENCY = "USD"
RATE_TTL_SECONDS = 300

def generate_user_id(users):
    return max((user['user_id'] for user in users), default=0) + 1

def register_user(username, password):
    if not username or not password: raise ValidationError("Имя пользователя и пароль обязательны.")
    if len(password) < 4: raise ValidationError("Пароль должен быть не короче 4 символов.")

    if data_manager.get_user_by_username(username):
        raise UserNotFoundError(f"Имя пользователя '{username}' уже занято.")

    user_id = generate_user_id(data_manager.get_all_users())
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
    users = data_manager.get_all_users()
    users.append(new_user)
    data_manager.save_users(users)

    # Создаем портфель и сразу добавляем стартовый USD
    initial_usd_balance = Decimal("1000.00")
    new_portfolio = {"user_id": user_id, "wallets": {BASE_CURRENCY: {'balance': str(initial_usd_balance)}}}

    portfolios = data_manager.get_all_portfolios()
    portfolios.append(new_portfolio)
    data_manager.save_portfolios(portfolios)

    return user_id

def login_user(username, password):
    users = data_manager.get_user_by_username(username)
    if not users:
        raise UserNotFoundError(f"Пользователь '{username}' не найден")

    salt = users['salt']
    test_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    if test_hash != users['hashed_password']:
        raise InvalidCredentialsError("Неверный пароль")

    return users['user_id']

def show_portfolio(user_id, base_currency=BASE_CURRENCY):
    portfolio_data = data_manager.get_portfolio_by_user_id(user_id)
    rates_cache = rate_manager.get_rates()

    if not portfolio_data:
        raise UserNotFoundError(f"Портфель для пользователя с ID {user_id} не найден.")
    
    total_value = Decimal('0.0')
    portfolio_info = {}

    wallets = portfolio_data.get('wallets', {})
    if wallets:
        for curr, data in wallets.items():
            balance = data.get('balance', 0)
            if not isinstance(balance, Decimal):  # Преобразуем в Decimal, только если это не Decimal
                balance = Decimal(str(balance)).quantize(Decimal("0.0000"))
            
            value = Decimal('0.0')
            if curr == base_currency:
                value = balance
            else:
                rate_key = f"{curr}_{base_currency}"
                if 'rates' in rates_cache and rate_key in rates_cache['rates'] and 'rate' in rates_cache['rates'][rate_key]:
                    try:
                        rate_value = Decimal(rates_cache['rates'][rate_key]['rate'])
                        value = balance * rate_value
                    except (ValueError, TypeError):
                        value = Decimal('0.0')
                else:
                    value = Decimal('0.0')
            
            total_value += value
            portfolio_info[curr] = {"balance": balance, "value_in_base": value}
    
    return portfolio_info, total_value

def buy_currency(user_id, currency, amount):
    currency = currency.upper()

    if amount <= 0:
        raise ValidationError("'amount' должен быть положительным числом")

    portfolio_raw = data_manager.get_portfolio_by_user_id(user_id)
    if not portfolio_raw: raise UserNotFoundError("Портфель не найден.")

    rates = rate_manager.get_rates()
    rate_key = f"{currency}_{BASE_CURRENCY}"

    # Проверяем наличие ключа 'rates'
    if 'rates' not in rates or rate_key not in rates['rates'] or 'rate' not in rates['rates'][rate_key]:
        raise ApiRequestError(f"Курс {currency}→USD недоступен.")

    rate = Decimal(rates['rates'][rate_key]['rate'])
    amount_dec = Decimal(str(amount))
    cost = amount_dec * rate

    if BASE_CURRENCY not in portfolio_raw['wallets']:
        portfolio_raw['wallets'][BASE_CURRENCY] = {'balance': '0.0'}

    usd_balance = portfolio_raw['wallets'][BASE_CURRENCY]['balance']

    #Преобразуем float/int/str в Decimal
    if isinstance(usd_balance, (int, float, str)):
        usd_balance = Decimal(str(usd_balance)).quantize(Decimal("0.0000"))
    else:
        usd_balance = Decimal('0.0')

    if usd_balance < cost:
        raise InsufficientFundsError(usd_balance, cost, BASE_CURRENCY)

    # Выполняем операцию
    portfolio_raw['wallets'][BASE_CURRENCY]['balance'] = str((usd_balance - cost).quantize(Decimal("0.0000")))

    if currency not in portfolio_raw['wallets']:
        portfolio_raw['wallets'][currency] = {'balance': '0.0'}

    currency_balance = portfolio_raw['wallets'][currency]['balance']
    #Преобразуем float/int/str в Decimal
    if isinstance(currency_balance, (int, float, str)):
        currency_balance = Decimal(str(currency_balance)).quantize(Decimal("0.0000"))
    else:
        currency_balance = Decimal('0.0')

    portfolio_raw['wallets'][currency]['balance'] = str((currency_balance + amount_dec).quantize(Decimal("0.0000"))) #Добавил quantize
    
    # Находим индекс портфеля пользователя
    portfolios = data_manager.get_all_portfolios()
    for i, portfolio in enumerate(portfolios):
        if portfolio['user_id'] == user_id:
            portfolios[i] = portfolio_raw
            break
    
    data_manager.save_portfolios(portfolios)

    return f"Покупка выполнена: {amount_dec:.4f} {currency} по курсу {rate:.2f} USD/{currency}"

def sell_currency(user_id, currency, amount):
    currency = currency.upper()

    if amount <= 0:
        raise ValidationError("'amount' должен быть положительным числом")

    portfolio_raw = data_manager.get_portfolio_by_user_id(user_id)
    if not portfolio_raw: raise UserNotFoundError("Портфель не найден.")

    if currency not in portfolio_raw['wallets']:
        raise CurrencyNotFoundError()
    
    currency_balance = portfolio_raw['wallets'][currency]['balance']
    if isinstance(currency_balance, (int, float, str)):
        currency_balance = Decimal(str(currency_balance)).quantize(Decimal("0.0000"))
    else:
        currency_balance = Decimal('0.0')

    if currency_balance < amount:
        raise InsufficientFundsError(currency_balance, amount, currency)

    rates = rate_manager.get_rates()
    rate_key = f"{currency}_{BASE_CURRENCY}"

    # Проверяем наличие ключа 'rates'
    if 'rates' not in rates or rate_key not in rates['rates'] or 'rate' not in rates['rates'][rate_key]:
        raise ApiRequestError(f"Курс {currency}→USD недоступен.")

    rate = Decimal(rates['rates'][rate_key]['rate'])
    amount_dec = Decimal(str(amount))
    revenue = amount_dec * rate

    # Выполняем операцию
    portfolio_raw['wallets'][currency]['balance'] = str((currency_balance - amount_dec).quantize(Decimal("0.0000")))

    if BASE_CURRENCY not in portfolio_raw['wallets']:
        portfolio_raw['wallets'][BASE_CURRENCY] = {'balance': '0.0'}

    usd_balance = portfolio_raw['wallets'][BASE_CURRENCY]['balance']
    if isinstance(usd_balance, (int, float, str)):
        usd_balance = Decimal(str(usd_balance)).quantize(Decimal("0.0000"))
    else:
        usd_balance = Decimal('0.0')

    portfolio_raw['wallets'][BASE_CURRENCY]['balance'] = str((usd_balance + revenue).quantize(Decimal("0.0000")))

    # Находим индекс портфеля пользователя
    portfolios = data_manager.get_all_portfolios()
    for i, portfolio in enumerate(portfolios):
        if portfolio['user_id'] == user_id:
            portfolios[i] = portfolio_raw
            break

    data_manager.save_portfolios(portfolios)

    return f"Продажа выполнена: {amount_dec:.4f} {currency} по курсу {rate:.2f} USD/{currency}"

def get_rate(from_currency, to_currency):
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    rates = rate_manager.get_rates()
    rate_key = f"{from_currency}_{to_currency}"

    rate_data = rates.get(rate_key)

    if rate_data:
        updated_at = rate_data.get('updated_at')
        if updated_at:
            updated_at_dt = datetime.fromisoformat(updated_at)
            if (datetime.utcnow() - updated_at_dt).total_seconds() <= RATE_TTL_SECONDS:
                rate_value = Decimal(rate_data['rate']) if isinstance(rate_data['rate'], (str, Decimal)) else rate_data['rate']
                return f"Курс {from_currency}→{to_currency}: {rate_value:.8f} (обновлено: {updated_at[:19]})"

    try:
        new_rates = rate_manager.refresh_rates()
        rate_key = f"{from_currency}_{to_currency}"
        if rate_key in new_rates and 'rate' in new_rates[rate_key]:
            rate_value = Decimal(new_rates[rate_key]['rate'])
            return f"Курс {from_currency}→{to_currency}: {rate_value:.8f} (обновлено: {new_rates[rate_key]['updated_at'][:19]})"
        else:
            raise ApiRequestError(f"Курс {from_currency}→{to_currency} по-прежнему недоступен после обновления.")
    except ApiRequestError as e:
        raise ApiRequestError(f"Данные о курсе недоступны: {e}")
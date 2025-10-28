# valutatrade_hub/decorators.py
import inspect
import logging
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)


def log_action(verbose=False):
    """
    Декоратор для логирования действий (buy, sell, register, login)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            username = None
            currency_code = None
            amount = None
            rate = None
            base = None
            result = "OK"
            error_type = None
            error_message = None

            #  Имитируем подпись
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            if 'username' in bound_args.arguments:
                username = bound_args.arguments['username']
            if 'user_id' in bound_args.arguments:
                user_id = bound_args.arguments['user_id']
            if 'currency' in bound_args.arguments:
                currency_code = bound_args.arguments['currency']
            if 'amount' in bound_args.arguments:
                amount = bound_args.arguments['amount']

            try:
                result_value = func(*args, **kwargs)
                return result_value
            except Exception as e:
                result = "ERROR"
                error_type = type(e).__name__
                error_message = str(e)
                raise
            finally:
                extra_info = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': func.__name__.upper(),
                    'username': username if username else user_id if 'user_id' in locals() else "Guest",
                    'currency_code': currency_code,
                    'amount': amount,
                    'rate': rate,
                    'base': base,
                    'result': result,
                    'error_type': error_type,
                    'error_message': error_message,
                }

                # Логируем
                log_message = f"{func.__name__.upper()} action by {extra_info.get('username')
                                                                   or 'Guest'} with result: {result}"

                # Добавляем детали в лог
                if verbose:
                    log_message += f" Details: {extra_info}"

                logger.info(log_message, extra=extra_info)

        return wrapper

    return decorator

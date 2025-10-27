# valutatrade_hub/decorators.py
import logging
from functools import wraps
import inspect
from datetime import datetime

logger = logging.getLogger(__name__)

def log_action(verbose=False):
    """
    Декоратор для логирования действий (buy, sell, register, login).
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract username and currency code from arguments
            username = None
            currency_code = None
            amount = None
            rate = None
            base = None
            result = "OK"
            error_type = None
            error_message = None

            # Try to intelligently extract arguments based on the function's signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()  # Fill in any missing default values

            if 'username' in bound_args.arguments:
                username = bound_args.arguments['username']
            if 'user_id' in bound_args.arguments:
                user_id = bound_args.arguments['user_id']
            if 'currency' in bound_args.arguments:
                currency_code = bound_args.arguments['currency']
            if 'amount' in bound_args.arguments:
                amount = bound_args.arguments['amount']

            try:
                # Run the actual function
                result_value = func(*args, **kwargs)
                return result_value
            except Exception as e:
                result = "ERROR"
                error_type = type(e).__name__
                error_message = str(e)
                raise # Re-raise the exception
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

                # Log the action with all relevant information
                log_message = f"{func.__name__.upper()} action by {extra_info.get('username') or 'Guest'} with result: {result}"

                # Add verbose logging if required (more details)
                if verbose:
                    log_message += f" Details: {extra_info}"

                logger.info(log_message, extra=extra_info) # Use extra for structured logging

        return wrapper
    return decorator
# valutatrade_hub/cli/interface.py (продолжение)
import argparse
import sys
from decimal import Decimal

from prettytable import PrettyTable

from ..core import usecases

# Импортируем измененные исключения
from ..core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
    InvalidCredentialsError,
    UserNotFoundError,
    ValidationError,
)
from ..infra.database import database_manager  # Import the database manager
from ..logging_config import configure_logging  # Import configure_logging
from ..parser_service.updater import updater


class CLIInterface:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="ValutaTrade Hub CLI")
        self.subparsers = self.parser.add_subparsers(dest="command", required=True)
        self.user_id = None  # Состояние сессии
        self.username = None  # Состояние имени пользователя

        self._setup_parsers()

    def _setup_parsers(self):
        # Парсеры для каждой команды
        register_parser = self.subparsers.add_parser("register", help="Создать нового пользователя")
        register_parser.add_argument("--username", required=True, help="Имя пользователя")
        register_parser.add_argument("--password", required=True, help="Пароль")
        register_parser.set_defaults(func=self.handle_register)

        login_parser = self.subparsers.add_parser("login", help="Войти в систему")
        login_parser.add_argument("--username", required=True, help="Имя пользователя")
        login_parser.add_argument("--password", required=True, help="Пароль")
        login_parser.set_defaults(func=self.handle_login)

        show_portfolio_parser = self.subparsers.add_parser("show-portfolio",
                                                           help="Показать портфель пользователя")
        show_portfolio_parser.add_argument("--base", default="USD",
                                           help="Базовая валюта для расчета общей стоимости (по умолчанию USD)")
        show_portfolio_parser.set_defaults(func=self.handle_show_portfolio)

        buy_parser = self.subparsers.add_parser("buy", help="Купить валюту")
        buy_parser.add_argument("--currency", required=True, help="Валюта для покупки (например, BTC)")
        buy_parser.add_argument("--amount", required=True, type=float, help="Количество для покупки")
        buy_parser.set_defaults(func=self.handle_buy)

        sell_parser = self.subparsers.add_parser("sell", help="Продать валюту")
        sell_parser.add_argument("--currency", required=True, help="Валюта для продажи (например, BTC)")
        sell_parser.add_argument("--amount", required=True, type=float, help="Количество для продажи")
        sell_parser.set_defaults(func=self.handle_sell)

        get_rate_parser = self.subparsers.add_parser("get-rate", help="Получить курс валюты")
        get_rate_parser.add_argument("--from", required=True, dest="from_currency", help="Исходная валюта")
        get_rate_parser.add_argument("--to", required=True, dest="to_currency", help="Целевая валюта")
        get_rate_parser.set_defaults(func=self.handle_get_rate)

        # НОВАЯ КОМАНДА: update-rates
        update_rates_parser = self.subparsers.add_parser("update-rates",
                                                         help="Запустить немедленное обновление курсов валют")
        update_rates_parser.add_argument("--source", choices=['coingecko', 'exchangerate'],
                                         help="Обновить данные только из указанного источника")
        update_rates_parser.set_defaults(func=self.handle_update_rates)

        # НОВАЯ КОМАНДА: show-rates (улучшенная версия get-rate)
        show_rates_parser = self.subparsers.add_parser("show-rates",
                                                       help="Показать актуальные курсы из локального кеша")
        show_rates_parser.add_argument("--currency", help="Показать курс только для указанной валюты")
        show_rates_parser.add_argument("--top", type=int, help="Показать N самых дорогих криптовалют")
        show_rates_parser.add_argument("--base", default="USD", help="Базовая валюта для отображения курсов")
        show_rates_parser.set_defaults(func=self.handle_show_rates)

    def handle_register(self, args):
        try:
            user_id = usecases.register_user(args.username, args.password)
            print(f"Пользователь '{args.username}' зарегистрирован (id={user_id}). "
                  + f"Войдите: login --username {args.username} --password ****")
        except (ValidationError, UserNotFoundError) as e:
            print(f"Ошибка: {e}")

    def handle_login(self, args):
        try:
            user_id = usecases.login_user(args.username, args.password)
            self.user_id = user_id
            self.username = args.username
            print(f"Вы вошли как '{args.username}'")
        except UserNotFoundError:
            print("Ошибка: Пользователь не найден")
        except InvalidCredentialsError:
            print("Ошибка: Неверный пароль")
        except ValidationError as e:
            print(f"Ошибка: {e}")

    def handle_show_portfolio(self, args):
        if not self.user_id:
            print("Ошибка: Сначала выполните login")
            return

        try:
            portfolio_data, total_value = usecases.show_portfolio(self.user_id, args.base.upper())

            table = PrettyTable()
            table.field_names = ["Валюта", "Баланс", f"Стоимость ({args.base.upper()})"]
            table.align["Валюта"] = "l"
            table.align["Баланс"] = "r"
            table.align[f"Стоимость ({args.base.upper()})"] = "r"

            if not portfolio_data:
                table.add_row(["", "", ""])
            else:
                for currency, data in portfolio_data.items():
                    # Форматирование выводим в CLI
                    table.add_row([currency, f"{data['balance']:.4f}", f"{data['value_in_base']:.2f}"])

            print(f"Портфель пользователя '{self.username}' (база: {args.base.upper()}):")
            print(table)
            print("-" * 40)
            print(f"ИТОГО: {total_value:.2f} {args.base.upper()}")

        except (ValidationError, UserNotFoundError) as e:
            print(f"Ошибка: {e}")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: Неизвестная базовая валюта '{e.code}'")

    def handle_buy(self, args):
        if not self.user_id:
            print("Ошибка: Сначала выполните login")
            return

        try:
            amount = Decimal(str(args.amount))
            result = usecases.buy_currency(self.user_id, args.currency.upper(), amount)
            print(result)
        except ValidationError as e:
            print(f"Ошибка: {e}")
        except InsufficientFundsError as e:
            print(e)  # Теперь печатает сообщение из исключения, которое логируется декоратором
        except ApiRequestError:
            print(f"Ошибка: Не удалось получить курс для {args.currency.upper()}→USD")
        except CurrencyNotFoundError as e:
            print(f"Ошибка: Неизвестная валюта '{e.code}'")

    def handle_sell(self, args):
        if not self.user_id:
            print("Ошибка: Сначала выполните login")
            return

        try:
            amount = Decimal(str(args.amount))
            result = usecases.sell_currency(self.user_id, args.currency.upper(), amount)
            print(result)
        except ValidationError as e:
            print(f"Ошибка: {e}")
        except CurrencyNotFoundError as e:
            print(e)  # Печатаем сообщение из исключения
        except InsufficientFundsError as e:
            print(e)  # Печатаем сообщение из исключения
        except ApiRequestError:
            print(f"Ошибка: Не удалось получить курс для {args.currency.upper()}→USD")

    def handle_get_rate(self, args):
        try:
            result = usecases.get_rate(args.from_currency.upper(), args.to_currency.upper())
            print(result)
        except CurrencyNotFoundError as e:
            print(f"Курс {e.code} недоступен. Попробуйте команду 'get-rate' с известными валютами.")
        except ApiRequestError:
            print(f"Курс {args.from_currency.upper()}→{args.to_currency.upper()} недоступен. Повторите попытку позже.")

    def handle_update_rates(self, args):
        print("INFO: Starting rates update...")
        try:
            updater.run_update(args.source)
        except ApiRequestError as e:
            print(f"ERROR: Failed during update: {e}")
        except Exception as e:
            print(f"FATAL ERROR during update: {e}")

    def handle_show_rates(self, args):
        """
        Отображает текущие курсы валют из кэша.
        """
        try:
            rates_data = database_manager.get_rates()
            rates = rates_data.get('pairs', {})
            last_refresh = rates_data.get('last_refresh', 'N/A')

           # Фильтрация
            filtered_rates = rates
            if args.currency:
                target_currency = args.currency.upper()
                # Фильтруем пары, где target_currency либо FROM, либо TO
                filtered_rates = {
                    pair: data for pair, data in rates.items()
                    if pair.startswith(target_currency + '_') or pair.endswith('_' + target_currency)
                }

            # Подготовка данных для сортировки (если --top)
            sortable_data = []
            for pair, data in filtered_rates.items():
                try:
                    rate = Decimal(data['rate'])
                    sortable_data.append((pair, rate, data))
                except (ValueError, TypeError):
                    print(f"WARNING: Invalid rate for {pair}, skipping.")

            sortable_data.sort(key=lambda x: x[0])

            if args.top:
                try:
                    top_n = int(args.top)
                    sortable_data = sortable_data[:top_n]
                except ValueError:
                    print("Ошибка: --top должно быть целым числом.")
                    return

            print(f"Rates from cache (updated at {last_refresh}):")
            table = PrettyTable()
            table.field_names = ["Пара", "Курс", "Обновлено", "Источник"]
            table.align = "l"
            for pair, rate, data in sortable_data:
                table.add_row([
                    pair,
                    f"{rate:.8f}",
                    data['updated_at'][:19],
                    data['source']
                ])
            print(table)

        except Exception as e:
            print(f"Ошибка при отображении курсов: {e}")

    def run(self):
        configure_logging()  # Configure logging at the start

        # Логика интерактивного режима
        if len(sys.argv) == 1:
            print("--- ValutaTrade Hub CLI (Интерактивный режим) ---")
            print("Введите команды или 'exit' для выхода.")
            while True:
                try:
                    user_input = input(f"VTH ({'Logged' if self.user_id else 'Guest'})> ")
                    if not user_input.strip():
                        continue

                    if user_input.lower() == 'exit':
                        print("Завершение работы.")
                        break

                    args_list = user_input.split()
                    if not args_list:
                        continue

                    command = args_list[0]
                    args_list = args_list[1:]

                    # Парсинг для интерактивного режима
                    if command == "register":
                        parser_temp = argparse.ArgumentParser()
                        parser_temp.add_argument("--username", required=True)
                        parser_temp.add_argument("--password", required=True)
                        args = parser_temp.parse_args(args_list)
                        self.handle_register(args)
                    elif command == "login":
                        parser_temp = argparse.ArgumentParser()
                        parser_temp.add_argument("--username", required=True)
                        parser_temp.add_argument("--password", required=True)
                        args = parser_temp.parse_args(args_list)
                        self.handle_login(args)
                    elif command == "show-portfolio":
                        parser_temp = argparse.ArgumentParser()
                        parser_temp.add_argument("--base", default="USD")
                        args = parser_temp.parse_args(args_list)
                        self.handle_show_portfolio(args)
                    elif command == "buy":
                        parser_temp = argparse.ArgumentParser()
                        parser_temp.add_argument("--currency", required=True)
                        parser_temp.add_argument("--amount", required=True, type=float)
                        args = parser_temp.parse_args(args_list)
                        self.handle_buy(args)
                    elif command == "sell":
                        parser_temp = argparse.ArgumentParser()
                        parser_temp.add_argument("--currency", required=True)
                        parser_temp.add_argument("--amount", required=True, type=float)
                        args = parser_temp.parse_args(args_list)
                        self.handle_sell(args)
                    elif command == "get-rate":
                        parser_temp = argparse.ArgumentParser()
                        parser_temp.add_argument("--from", required=True, dest="from_currency")
                        parser_temp.add_argument("--to", required=True, dest="to_currency")
                        args = parser_temp.parse_args(args_list)
                        self.handle_get_rate(args)
                    elif command == "update-rates":
                        parser_temp = argparse.ArgumentParser()
                        parser_temp.add_argument("--source", choices=['coingecko', 'exchangerate'], default=None)
                        args = parser_temp.parse_args(args_list)
                        self.handle_update_rates(args)
                    elif command == "show-rates":
                        parser_temp = argparse.ArgumentParser()
                        parser_temp.add_argument("--currency")
                        parser_temp.add_argument("--top", type=int)
                        parser_temp.add_argument("--base", default="USD")
                        args = parser_temp.parse_args(args_list)
                        self.handle_show_rates(args)
                    else:
                        print("Ошибка: Неизвестная команда")

                except SystemExit:  # argparse вызывает SystemExit при ошибках
                    pass
                except Exception as e:
                    print(f"Непредвиденная ошибка: {e}")

        else:
            try:
                args = self.parser.parse_args()
                if hasattr(args, 'func'):
                    args.func(self, args)
            except SystemExit:
                pass
            except Exception as e:
                print(f"Непредвиденная ошибка: {e}")


def main():
    cli = CLIInterface()
    cli.run()

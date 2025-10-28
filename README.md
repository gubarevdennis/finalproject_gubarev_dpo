# ValutaTrade Hub

## Описание

ValutaTrade Hub - это CLI-приложение для управления криптовалютным и фиатным портфелем. Пользователи могут регистрироваться, входить в систему, покупать и продавать валюты, просматривать свой портфель и узнавать актуальные курсы валют.

## Структура каталогов

finalproject_gubarev_dpo/ │
├── data/ │ ├── users.json
│ ├── portfolios.json
│ ├── rates.json # локальный кэш для Core Service │ └── exchange_rates.json # хранилище Parser Service (исторические данные).json
├── valutatrade_hub/ │ ├── init.py │ ├── logging_config.py
│ ├── decorators.py
│ ├── core/ │ │ ├── init.py │ │ ├── currencies.py
│ │ ├── exceptions.py
│ │ ├── models.py
│ │ ├── usecases.py
│ │ └── utils.py
│ ├── infra/ │ │ ├─ init.py │ │ ├── settings.py
│ │ └── database.py
│ ├── parser_service/ │ │ ├── init.py │ │ ├── config.py # конфигурация API и параметров обновления │ │ ├── api_clients.py # работа с внешними API │ │ ├── updater.py # основной модуль обновления курсов │ │ ├── storage.py # операции чтения/записи exchange_rates.json │ │ └── scheduler.py # планировщик периодического обновления │ └── cli/ │ ├─ init.py │ └─ interface.py
│ ├── main.py ├── Makefile ├── poetry.lock ├── pyproject.toml ├── README.md └── .gitignore

*   `data/`: Хранит данные пользователей (`users.json`), портфели (`portfolios.json`), актуальные курсы (`rates.json`) и историю курсов (`exchange_rates.json`).
*   `valutatrade_hub/`: Основной пакет приложения.
    *   `core/`: Содержит бизнес-логику: модели данных, use cases и исключения.
    *   `infra/`: Содержит инфраструктурный код: настройки, подключение к базе данных.
    *   `parser_service/`: Отвечает за получение и обновление курсов валют из внешних API.
    *   `cli/`: Интерфейс командной строки.
*   `main.py`: Точка входа в приложение.
*   `Makefile`: Содержит команды для сборки, установки и запуска приложения.
*   `poetry.lock`: Файл блокировки зависимостей Poetry.
*   `pyproject.toml`: Файл конфигурации Poetry.

## Установка

### С использованием Poetry

1. Установите Poetry, если у вас его еще нет под вашу операционную систему:

    ```bash
    brew install poetry
    ```

2. Установите зависимости проекта:

    ```bash
    poetry install
    ```

### С использованием Makefile

1. Установите зависимости проекта:

    ```bash
    make install
    ```

## Запуск

1. Запустите с помощью Poetry:

    ```bash
    poetry run project
    ```
2. Запустите с помощью Makefile:

    ```bash
    make project


## Команды CLI

### Регистрация пользователя
project register –username <имя_пользователя> –password <пароль>
 

### Вход пользователя
project login –username <имя_пользователя> –password <пароль>
 

### Просмотр портфеля
project show-portfolio [–base <валюта>]
 

*   `--base`: Базовая валюта для отображения стоимости портфеля (по умолчанию USD).

### Покупка валюты
project buy –currency <код_валюты> –amount <сумма>
 

### Продажа валюты
project sell –currency <код_валюты> –amount <сумма>

### Получение курса валюты
project get-rate –pair <валютная_пара>
 

Пример: `project get-rate --pair BTC/USD`

### Просмотр курсов валют
project show-rates [–currency <код_валюты>] [–top <количество>]
 

*   `--currency`: Фильтр по валюте.
*   `--top`: Отображает N самых дорогих валют.

### Обновление курсов валют
project update-rates [–source <источник>]
 

*   `--source`: Источник данных (`coingecko` или `exchangerate`). По умолчанию - оба.

## Кэш и TTL

Приложение использует локальный кэш (`rates.json`) для хранения актуальных курсов валют. Parser Service (компонент, отвечающий за обновление курсов) периодически обновляет этот кэш.
Срок годности кэша (TTL) задается в файле `valutatrade_hub/infra/settings.py`. Если курс валюты в кэше устарел, приложение сообщит об этом пользователю и предложит обновить курсы.

## Запуск Parser Service

Parser Service можно запустить вручную с помощью команды `project update-rates`.
Для автоматического обновления курсов необходимо настроить планировщик задач (например, cron) для периодического запуска этой команды.

## API ключ ExchangeRate-API

Для работы с ExchangeRate-API требуется API ключ. Получить его можно, зарегистрировавшись на сайте [https://www.exchangerate-api.com/](https://www.exchangerate-api.com/).

## Демонстрация работы (asciinema)
[![asciicast](https://asciinema.org/a/fqkrJNFFiKvxz1FOPmEzFdRFM.svg)](https://asciinema.org/a/fqkrJNFFiKvxz1FOPmEzFdRFM)
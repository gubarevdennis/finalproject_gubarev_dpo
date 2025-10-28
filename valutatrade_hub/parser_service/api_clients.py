# valutatrade_hub/parser_service/api_clients.py
from decimal import Decimal
from typing import Dict

import requests

from ..core.exceptions import ApiRequestError
from .config import parser_config


class BaseApiClient:
    def fetch_rates(self) -> Dict[str, Decimal]:
        raise NotImplementedError("Must be implemented by subclasses")


class CoinGeckoClient(BaseApiClient):
    def fetch_rates(self) -> Dict[str, Decimal]:
        config = parser_config
        crypto_ids = ",".join(config.CRYPTO_ID_MAP[code] for code in config.CRYPTO_CURRENCIES)

        url = f"{config.COINGECKO_URL}?ids={crypto_ids}&vs_currencies={config.BASE_FIAT_CURRENCY.lower()}"

        try:
            response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            standardized_rates = {}
            for code, coin_id in config.CRYPTO_ID_MAP.items():
                pair_key = f"{code}_{config.BASE_FIAT_CURRENCY}"
                if coin_id in data and config.BASE_FIAT_CURRENCY.lower() in data[coin_id]:
                    rate = Decimal(str(data[coin_id][config.BASE_FIAT_CURRENCY.lower()]))
                    standardized_rates[pair_key] = rate

            return standardized_rates

        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors
            if e.response.status_code == 429:
                raise ApiRequestError("CoinGecko is rate limiting us. Please try again later.")
            else:
                raise ApiRequestError(f"CoinGecko API request failed with status code {e.response.status_code}: {e}")
        except requests.exceptions.HTTPError as e:
            raise ApiRequestError(f"CoinGecko API error: {e}") from e


class ExchangeRateApiClient(BaseApiClient):
    def fetch_rates(self) -> Dict[str, Decimal]:
        config = parser_config
        key = config.EXCHANGERATE_API_KEY
        base = config.BASE_FIAT_CURRENCY

        if not key or key == "DEFAULT_KEY":
            raise ApiRequestError("API Key for ExchangeRate-API is missing or default.")

        url = f"{config.EXCHANGERATE_API_URL}/{key}/latest/{base}"

        try:
            response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()  # Raises HTTPError for bad responses

            data = response.json()

            if data.get("result") != "success":
                error_type = data.get('error-type', 'Unknown')
                if error_type == 'invalid-key':
                    raise ApiRequestError("Invalid API key for ExchangeRate-API.")
                else:
                    raise ApiRequestError(f"ExchangeRate-API returned failure: {error_type}")

            standardized_rates = {}
            for fiat_code, rate_str in data.get("conversion_rates", {}).items():
                if fiat_code in config.FIAT_CURRENCIES:
                    pair_key = f"{fiat_code}_USD"
                    rate = Decimal(str(rate_str))
                    standardized_rates[pair_key] = rate

            return standardized_rates

        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors
            if e.response.status_code == 401:
                raise ApiRequestError("ExchangeRate-API: Authentication failed. Check your API key.")
            elif e.response.status_code == 403:
                raise ApiRequestError("ExchangeRate-API: You don't have permission to access this resource.")
            elif e.response.status_code == 429:
                raise ApiRequestError("ExchangeRate-API is rate limiting us. Please try again later.")
            else:
                raise ApiRequestError(f"ExchangeRate-API request failed with status code {e.response.status_code}: {e}")
        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Network error: {e}") from e

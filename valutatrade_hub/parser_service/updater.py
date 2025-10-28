# valutatrade_hub/parser_service/updater.py
import logging
from datetime import datetime  # Add this import
from decimal import Decimal  # Correct import
from typing import Dict, Optional

from ..core.exceptions import ApiRequestError
from .api_clients import CoinGeckoClient, ExchangeRateApiClient
from .storage import storage

logger = logging.getLogger('valutatrade_hub.parser_service')

class RatesUpdater:
    def __init__(self):
        self.coingecko_client = CoinGeckoClient()
        self.exchangerate_client = ExchangeRateApiClient() # Fix the typo
        self._SOURCE = "Combined"

    def run_update(self, source_filter: Optional[str] = None):
        all_rates: Dict[str, Decimal] = {}

        # Контекст для логов парсера
        base_log_extra = {
            "action": "UPDATE_RATES",
            "username": "ParserService",
            "currency_code": "N/A",
            "amount": "N/A",
            "rate": "N/A",
            "base": "N/A",
            "result": "OK",
            "error_type": "N/A",
            "error_message": "N/A"
        }

        logger.info("Starting rates update.", extra={**base_log_extra, "log_message":
                                                      "Starting rates update."}) # Changed here

        # 1. CoinGecko Update
        if source_filter is None or source_filter == "coingecko":
            try:
                cg_rates = self.coingecko_client.fetch_rates()
                all_rates.update(cg_rates)
                self._SOURCE = "coingecko"
                msg = f"Fetching from CoinGecko... OK ({len(cg_rates)} rates)"
                logger.info(msg, extra={**base_log_extra, "log_message": msg, "result": "OK"})
            except ApiRequestError as e:
                msg = f"Failed to fetch from CoinGecko: {e}"
                logger.error(msg, extra={**base_log_extra, "log_message": msg, "result":
                                          "ERROR", "error_type": type(e).__name__, "error_message": str(e)})

        # 2. ExchangeRate-API Update
        if source_filter is None or source_filter == "exchangerate":
            try:
                er_rates = self.exchangerate_client.fetch_rates()
                all_rates.update(er_rates)
                self.SOURCE = "exchangerate"
                msg = f"Fetching from ExchangeRate-API... OK ({len(er_rates)} rates)"
                logger.info(msg, extra={**base_log_extra, "log_message": msg, "result": "OK"}) # Changed here
            except ApiRequestError as e:
                msg = f"Failed to fetch from ExchangeRate-API: {e}"
                logger.error(msg, extra={**base_log_extra, "log_message": msg, "result":
                                          "ERROR", "error_type": type(e).__name__, "error_message": str(e)})

        # 3. Save combined rates
        if all_rates:
            # Save to rates.json (snapshot)
            updated_count = storage.save_current_rates(all_rates, source=self._SOURCE)

            # Формирование ответа для CLI
            if updated_count > 0:
                print(f"Update successful. Total rates updated: {updated_count}." +
                      f"Last refresh: {datetime.utcnow().isoformat()[:19]}")
            else:
                print("Update completed, but no new rates were saved.")
        else:
            print("Update failed: No rates were fetched from any source.")


updater = RatesUpdater()

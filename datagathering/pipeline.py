"""
Phase 1 Pipeline Runner — fetches option chains from the configured provider
and pushes them into the Redis cache for Phase 2 consumption.

Run with: python datagathering/pipeline.py
Control the provider via DATA_PROVIDER in .env (yfinance|tradier|theta)
"""
import os
import logging
import yaml
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from storage.cache_manager import push_chain

load_dotenv()
logger = logging.getLogger(__name__)


def load_config():
    path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.yaml')
    with open(path) as f:
        return yaml.safe_load(f)


def get_provider():
    provider_name = os.getenv("DATA_PROVIDER", "yfinance").lower()
    if provider_name == "yfinance":
        from datagathering.providers.yfinance_provider import YFinanceProvider
        return YFinanceProvider()
    elif provider_name == "tradier":
        from datagathering.providers.tradier_provider import TradierProvider
        return TradierProvider()
    elif provider_name == "theta":
        from datagathering.providers.theta_provider import ThetaProvider
        return ThetaProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use yfinance|tradier|theta")


def run():
    config = load_config()
    tickers = config.get("tickers", [])
    provider = get_provider()
    logger.info(f"Pipeline started | Provider: {provider.name} | Tickers: {tickers}")

    total = 0
    for ticker in tickers:
        logger.info(f"Fetching chain for {ticker}...")
        ticks = provider.fetch_chain(ticker)
        count = push_chain(ticks)
        total += count
        logger.info(f"{ticker}: {count} ticks pushed to Redis")

    logger.info(f"Pipeline complete. Total ticks in cache: {total}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()

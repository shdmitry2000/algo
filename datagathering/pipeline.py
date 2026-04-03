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
    elif provider_name == "file_folder":
        from datagathering.providers.file_folder_provider import FileFolderProvider, resolve_chain_files_dir

        chain_dir = resolve_chain_files_dir(os.getenv("CHAIN_FILES_DIR", ""), os.path.join(os.path.dirname(__file__), ".."))
        return FileFolderProvider(chain_dir)
    else:
        raise ValueError(f"Unknown provider: {provider_name}. Use yfinance|tradier|theta|file_folder")


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
        
        # Auto-trigger Phase 2 scan for this symbol (all its expirations)
        trigger_phase2_scan(ticker)

    logger.info(f"Pipeline complete. Total ticks in cache: {total}")


def _run_scan_bg(symbol: str) -> None:
    """Worker function that runs Phase 2 scan in background process."""
    import logging
    import sys
    
    # Configure logging for child process
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    logger = logging.getLogger(__name__)
    
    try:
        from filters.phase2strat1.scan import run_scan_for_symbol
        logger.info(f"[pipeline] Background: Triggering Phase 2 scan for {symbol}...")
        result = run_scan_for_symbol(symbol)
        logger.info(f"[pipeline] Background: Phase 2 scan complete for {symbol}: {result.get('signals_upserted', 0)} signals")
    except Exception as e:
        logger.error(f"[pipeline] Background: Phase 2 scan failed for {symbol}: {e}")
        import traceback
        logger.error(traceback.format_exc())


def trigger_phase2_scan(symbol: str) -> None:
    """
    Auto-trigger Phase 2 scan for a symbol after its data is loaded.
    Runs in background to avoid blocking the pipeline.
    """
    import multiprocessing
    p = multiprocessing.Process(target=_run_scan_bg, args=(symbol,))
    p.start()
    logger.info(f"[pipeline] Spawned background Phase 2 scan for {symbol} (PID will be assigned)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()

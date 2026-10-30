import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import math

tickers = ["JPM", "BAC", "C", "WFC", "GS", "MS", "XOM", "CVX", "COP", "SLB", "KO", "PEP"]

def extract_prices(data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    price_dict: dict[str, pd.Series] = {}

    for ticker in tickers:
        if (ticker, "Adj Close") in data.columns:
            price_dict[ticker] = data[(ticker, "Adj Close")]
        elif (ticker, "Close") in data.columns:
            price_dict[ticker] = data[(ticker, "Close")]
        else:
            raise KeyError(f"ERROR: No suitable price column found for {ticker}")
    
    prices = pd.DataFrame(price_dict).sort_index().dropna()
    return prices


def download_data(tickers: list[str],
                  start_date: str,
                  end_date: str,
                  interval: str) -> pd.DataFrame:
    raw = yf.download(
        tickers = tickers,
        start   = datetime.date.fromisoformat(start_date),
        end     = datetime.date.fromisoformat(end_date),
        interval= interval,
        group_by= "ticker",
        auto_adjust = False,
        progress = False
    )
    prices = extract_prices(raw, tickers)
    print(f"INFO: successful download of {tickers} data")
    return prices


def get_log_returns(prices: pd.DataFrame):    
    prices       = prices.sort_index()
    valid_prices = (prices > 0).all(axis=1)
    valid_prices = prices.loc[valid_prices]

    returns = np.log(prices/prices.shift(1))
    return returns.dropna()

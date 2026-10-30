import pandas as pd

from strategies import pairs_signal
import data

def main():
    prices = data.download_data(data.tickers, "2018-01-01", "2026-10-26", "1d")
    position, sharpe = pairs_signal(prices)

    print("\nPairs trading results")
    print("-" * 40)

    for pair in position:
        print(f"Pair: {pair}")
        print(f"Final PnL: {position[pair]:.2f}")
        print(f"Annualized Sharpe ratio: {sharpe[pair]:.4f}")


if __name__ == "__main__":
    main()

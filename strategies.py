import pandas as pd
import numpy as np
from itertools import combinations

# Pairs trading
# 
# Find a pair of stocks whose prices moved together historically
# If the spread widens  -> short the winner and buy the loser

def get_pairs(prices_norm: pd.DataFrame, top = 1) -> list[tuple]:
    # For all tickers combinations measure the distance
    # between normalized prices. This defines similarity
    # in a pair of stocks
    
    distances = []
    # combinations returns objects consisting in all the possible
    # sets of 2 elements extracted from the tickers
    for a, b in combinations(prices_norm.columns, 2):
        spread = prices_norm[a] - prices_norm[b]
        dist   = (spread**2).sum()
        distances.append((a, b, dist))
    distances.sort(key=lambda x : x[2]) # sort by increasing distance
    return distances[:top]


def get_spread_stdev(spreads: pd.DataFrame,
                     stretch_factor: float) -> dict:
    # Calculate the spread stdev over the selected formation period
    # and return the information as a dict
    mapping = {}
    for name in spreads.columns:
        mapping[name] = stretch_factor * spreads[name].std()
    return mapping


def trade(prices: pd.DataFrame,
          spreads: pd.DataFrame,
          thresholds: dict,
          reference_prices: pd.Series,
          previous_spread: pd.Series,
          capital: float = 10000.0) -> tuple[dict, dict[str, pd.Series]]:
    position = {}
    returns  = {}

    def execute_trade(A, pA, B, pB):
        return -(A*pA + B*pB)

    # For each pair compare their spread with the threshold
    # and then (maybe) do something in the market
    for name in spreads.columns:
        equity = [0.]
        stock_name_A, stock_name_B  = name.split("-")
        stock_A, stock_B = 0, 0
        cash = 0
        notional = capital / 2.0
        units_A = notional / reference_prices[stock_name_A]
        units_B = notional / reference_prices[stock_name_B]
        print(stock_name_A, stock_name_B)
        for i in range (len(spreads[name])):
            if i == 0:
                curr_spread = previous_spread[name]
            else:
                curr_spread = spreads[name].iloc[i-1]
            price_A = prices[stock_name_A].loc[spreads.index[i]]
            price_B = prices[stock_name_B].loc[spreads.index[i]]
            if stock_A < 0 and curr_spread <= 0:
                # Close short-A, long-B position
                print("Closing position sA lB", i)
                cash += execute_trade(-stock_A, price_A, -stock_B, price_B)
                stock_A, stock_B = 0, 0
            elif stock_A > 0 and curr_spread >= 0:
                # Close long-A, short-B position
                print("Closing position lA sB", i)
                cash += execute_trade(-stock_A, price_A, -stock_B, price_B)
                stock_A, stock_B = 0, 0
            elif curr_spread >= thresholds[name] and stock_A == 0:
                print("Shorting A", i)
                stock_A = -units_A
                stock_B = +units_B
                cash += execute_trade(stock_A, price_A, stock_B, price_B)
            elif curr_spread <= -thresholds[name] and stock_A == 0:
                print("Shorting B", i)
                stock_A = +units_A
                stock_B = -units_B
                cash += execute_trade(stock_A, price_A, stock_B, price_B)
                
            equity.append(cash + stock_A * price_A + stock_B * price_B)

        # At the end we close the position
        if stock_A != 0:
            print(f"Final liquidation: {name}")
            print(f"Holdings: A={stock_A:.4f}, B={stock_B:.4f}")
        cash += execute_trade(-stock_A, price_A, -stock_B, price_B)
        position[name] = cash
        daily_pnl = pd.Series(equity).diff().dropna()
        daily_pnl.index = spreads.index
        returns[name] = daily_pnl / capital
        
    return position, returns


def get_sharpe_ratio(returns: dict[str, pd.Series]) -> dict:
    sharpe = {}
    for name, daily_returns in returns.items():
        volatility = daily_returns.std()
        if len(daily_returns) < 2 \
           or not np.isfinite(volatility) or volatility == 0:
            sharpe[name] = np.nan
        else:
            sharpe[name] = (np.sqrt(252) * daily_returns.mean() / volatility)
    return sharpe
            
def pairs_signal(prices: pd.DataFrame):
    # Normalize price trajectories
    normalized = pd.DataFrame()
    for index, val in enumerate(prices.columns):
        normalized[val] = prices[val]/prices.iloc[0,index]

    # Get the reference prices (first prices in the series)
    reference_prices = prices.iloc[0]
        
    # Formation period:
    # Here you define the stdev of spread
    #
    # Trading period:
    # - Here you open the position if the spread exceeds 2*stdev
    #   spread > 2*sigma  -> Short A, buy B
    #   spread < -2*sigma -> buy A, short B
    # - spread == 0 -> close positions
    # - liquidate positions when trading period ends

    # split formation/trading dataframes
    # using 80% of the available data
    split = int(len(normalized) * 0.8)
    formation_norm   = normalized[:split]
    trading_prices   = prices[split:]
    trading_norm     = normalized[split:]
    
    # Get a number of interesting pairs
    top_pairs = 1
    pairs = get_pairs(formation_norm, top_pairs)

    # Define the spread using the interesting pairs
    spreads = pd.DataFrame()

    for index, item in enumerate(pairs):
        name_A = pairs[index][0]
        name_B = pairs[index][1]
        name   = name_A + "-" + name_B
        spreads[name] = normalized[name_A] - normalized[name_B]


    stretch_factor = 2.5
    # This maps pairs to their spread std()
    threshold_map = get_spread_stdev(spreads[:split], stretch_factor)

    # Do the trading
    position, returns = trade(trading_prices, spreads[split:], threshold_map, reference_prices, spreads.iloc[split-1])
    sharpe = get_sharpe_ratio(returns)
    
    return position, sharpe

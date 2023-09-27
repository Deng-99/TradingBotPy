from datetime import datetime
import alpaca_trade_api as tradeapi
import numpy as np
import pandas as pd
import keys

# Initialize the Alpaca API client
api = tradeapi.REST(keys.API_KEY, keys.SECERET_KEY,
                    base_url='https://paper-api.alpaca.markets')

# Configuration parameters
limit = 100
barTimeframe = "1D"  # Daily timeframe
assetsToTrade = ["SPY", "NVDA", "AAPL", "AMD",
                 "TSLA", "AMZN", "SNOW", "MSFT", "SQ"]
positionSizing = 0.25
resistance_level = 4  # Define your resistance level

# Risk management parameters
risk_per_trade = 0.15  # 15% risk per trade
stop_loss_pct = 0.07  # 7% stop-loss


def calculate_position_size(symbol, stop_loss_pct, risk_per_trade):
    # Calculate position size based on stop loss and risk percentage
    account_info = api.get_account()
    equity = float(account_info.equity)
    stop_loss_price =  api.get_bars(symbol, barTimeframe, limit=1)[
        symbol][0].l * (1 - stop_loss_pct)
    position_size = (equity * risk_per_trade) / \
        (stop_loss_price - stop_loss_price * stop_loss_pct)
    return position_size


for symbol in assetsToTrade:
    # Fetch historical data
    historical_data = api.get_bars(
        symbol, barTimeframe, limit=limit).df[symbol]
    close_prices = historical_data['close'].values
    sma_50 = np.mean(close_prices[-50:])

    # Check if the price breaks above the SMA50
    if close_prices[-1] > sma_50:
        # Check if the price breaks above the resistance level and retests it
        if close_prices[-1] > resistance_level and close_prices[-2] <= resistance_level:
            try:
                open_positions = api.list_positions()
                open_position = next(
                    (pos for pos in open_positions if pos.symbol == symbol), None)

                # Calculate the position size based on risk management
                position_size = calculate_position_size(
                    symbol, stop_loss_pct, risk_per_trade)

                if open_position is None:
                    # No existing position, buy option contracts
                    api.submit_order(
                        symbol=symbol,
                        qty=int(position_size),
                        side='buy',
                        type='market',
                        time_in_force='gtc',
                        order_class='oto',
                        stop_loss={
                            'stop_price': close_prices[-1] * (1 - stop_loss_pct),
                        },
                    )
                    print(
                        f"Bought {int(position_size)} contracts of {symbol} options.")
            except Exception as e:
                print(f"Error executing {symbol} trade: {e}")

    # If the price falls below the SMA50, close any open position
    elif close_prices[-1] < sma_50:
        open_positions = api.list_positions()
        open_position = next(
            (pos for pos in open_positions if pos.symbol == symbol), None)

        if open_position is not None:
            try:
                api.submit_order(
                    symbol=symbol,
                    qty=int(open_position.qty),
                    side='sell',
                    type='market',
                    time_in_force='gtc',
                )
                print(
                    f"Sold {int(open_position.qty)} contracts of {symbol} options.")
            except Exception as e:
                print(f"Error closing {symbol} position: {e}")

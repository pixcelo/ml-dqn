import ccxt
import pandas as pd
from position_manager import PositionManager
from logger import Logger

class Trade:
    def __init__(self, config):
        self.api_key = config.get("exchange", "api_key")
        self.secret_key = config.get("exchange", "secret_key")
        self.exchange_name = config.get("exchange", "exchange_name")

        # Initialize exchange
        self.exchange = getattr(ccxt, self.exchange_name)({
            "apiKey": self.api_key,
            "secret": self.secret_key
        })

        self.logger = Logger("main")

    def get_ohlcv(self, timeframe):
        ohlcv = self.exchange.fetch_ohlcv("BTC/USDT", timeframe)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df[f"{timeframe}_timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index(f"{timeframe}_timestamp", inplace=True)
        df.columns = [f"{timeframe}_{col}" for col in df.columns]
        return df

    def get_market_data(self):
        timeframes = ["1m", "5m", "15m", "1h", "4h"]

        # Get OHLCV data for each timeframe
        ohlcv_data = [self.get_ohlcv(timeframe) for timeframe in timeframes]
        
        return ohlcv_data

    def execute_trade(self, prediction):
        # Execute trade based on prediction here
        position_manager = PositionManager(self.exchange, "BTC/USDT")
        position_size = position_manager.get_position_size()
        amount = 0.001

        if position_size == 0:
            if prediction == 1:
                retult = self.place_order("BTC/USDT", "buy", amount)
            else:
                retult = self.place_order("BTC/USDT", "sell", amount)
        else:
            if prediction == 1:
                pass
            else:
                pass
            
        return retult
    
    def place_order(self, symbol, side, position_size):
        try:
            order = self.exchange.create_order(
                        symbol=symbol, # "BTC/USDT",
                        type="market", # "limit",
                        side=side, # "buy",
                        amount=position_size,
                        price=None,
                        params={
                            'time_in_force': 'PostOnly',
                            'reduce_only': True
                        }
                    )
            
            return True
        
        except Exception as e:
            self.logger().error(f"An exception occurred: {e}")
            return False

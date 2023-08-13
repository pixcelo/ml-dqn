import ccxt
import pandas as pd
import requests
import time
import hmac
import uuid
import hashlib
import json
from urllib.parse import urlencode
from position_manager import PositionManager
from discord_notifier import DiscordNotifier
from account import Account
from logger import Logger
from ta.volatility import AverageTrueRange

class Trade:
    def __init__(self, config):
        self.api_key = config.get("exchange", "api_key")
        self.secret_key = config.get("exchange", "secret_key")
        self.exchange_name = config.get("exchange", "exchange_name")
        self.first_run = True
        self.portfolio = {
            'position': None,  # "long" or "short"
            'entry_price': None,
            'entry_point': 0,
            'trailing_stop': 0
        }

        # Initialize exchange
        self.exchange = getattr(ccxt, self.exchange_name)({
            "apiKey": self.api_key,
            "secret": self.secret_key,
            "enableRateLimit": True,
            'options': {'defaultType': 'linear'}
        })

        self.logger = Logger("trade")
        self.discord_notifier = DiscordNotifier(config)
        self.account = Account(self.exchange)
        self.recv_window=str(10000)
        self.url="https://api.bybit.com"
        # self.url="https://api-testnet.bybit.com" 
        self.mode = self.set_position_mode(0)
        self.qty = 0.008

    def get_ohlcv(self, timeframe):
        ohlcv = self.exchange.fetch_ohlcv("BTC/USDT", timeframe, limit=500)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df.set_index(pd.to_datetime(df["timestamp"], unit="ms"), inplace=True)
        df.drop(columns=["timestamp"], inplace=True)
        # df.columns = [f"{timeframe}_{col}" for col in df.columns]
        return df

    def get_market_data(self):
        ohlcv_data = self.get_ohlcv("1m")
        return ohlcv_data
        # timeframes = ["1m"] #["1m", "5m", "15m", "30m"]
        # # Get OHLCV data for each timeframe
        # ohlcv_data = [self.get_ohlcv(timeframe) for timeframe in timeframes]
        # self.logger().info("get market data.")
        # return ohlcv_data
    
    def prepare_data(self, df):
        # Calculate moving averages
        df['SMA20'] = df['close'].rolling(window=20).mean()

        average_true_range = AverageTrueRange(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=210
        )
        df['ATR'] = average_true_range.average_true_range()

        return df

    def execute_trade(self, df):
        self.check_balance()
        # Execute trade based on prediction here
        position_manager = PositionManager(self.exchange, "BTCUSDT")
        long_positions, short_positions = position_manager.separate_positions_by_side()

        amount = self.qty
        result = None

        action = self.decide_trade_action(long_positions, short_positions, df)

        if action == "entry_long":
            result = self.place_order("BTCUSDT", "Buy", amount)
        elif action == "entry_short":
            result = self.place_order("BTCUSDT", "Sell", amount)
        elif action == "exit_short":
            result = self.place_order("BTCUSDT", "Buy", amount)
        elif action == "exit_long":
            result = self.place_order("BTCUSDT", "Sell", amount)
        elif action == None:
            pass

        message = f"{action}: "

        if result is True:
            message += "The order was successful."
        elif result is False:
            message += "The order was failed."
        else:
            message += "Hold current position."
        
        print(message)
        return message
    
    def decide_trade_action(self, long_positions, short_positions, df):
        i = df.index[-1]
        atr = df.loc[i, 'ATR']
        close = df.loc[i, 'close']
        ma = df.loc[i, 'SMA20']

        prev_close = df.loc[df.index[-2], 'close'] if len(df) > 1 else None
        prev_ma = df.loc[df.index[-2], 'SMA20'] if len(df) > 1 else None

        # 利確と損切りの閾値
        TAKE_PROFIT = atr * 1 + (close * 0.001) 
        STOP_LOSS = atr * -1

        print(f"Timestamp: {i}, ATR: {atr:.2f}, Close: {close:.2f}, SMA20: {ma:.2f}, Prev Close: {prev_close:.2f}, Prev SMA20: {prev_ma:.2f}")

        if len(long_positions) > 0:
            self.portfolio['trailing_stop'] = max(self.portfolio['trailing_stop'], close - STOP_LOSS) if 'trailing_stop' in self.portfolio else close - STOP_LOSS
            profit = (close - self.portfolio['entry_price']) * (1 - self.commission_rate)
            if profit > TAKE_PROFIT or close < self.portfolio['trailing_stop']:
                return 'exit_long'
            else:
                return None
        elif len(short_positions) > 0:
            self.portfolio['trailing_stop'] = min(self.portfolio['trailing_stop'], close + STOP_LOSS) if 'trailing_stop' in self.portfolio else close + STOP_LOSS
            profit = (self.portfolio['entry_price'] - close) * (1 - self.commission_rate)
            if profit > TAKE_PROFIT or close > self.portfolio['trailing_stop']:
                return 'exit_short'
            else:
                return None
        elif prev_close is not None and prev_ma is not None \
            and prev_close < prev_ma and close > ma:
                self.portfolio['trailing_stop'] = 0
                self.portfolio['entry_price'] = close
                return "entry_long"
        elif prev_close is not None and prev_ma is not None \
            and prev_close > prev_ma and close < ma:
                self.portfolio['trailing_stop'] = 0
                self.portfolio['entry_price'] = close
                return 'entry_short'
        else:
            return None

    def place_order(self, symbol, side, amount):
        endpoint="/v5/order/create"
        method="POST"
        orderLinkId=uuid.uuid4().hex
        params = {
            "category": "linear",
            "symbol": symbol,
            "isLeverage": 1,
            "side": side,
            "orderType": "Market",
            "qty": str(amount),
            "orderLinkId": orderLinkId,
            "positionIdx": 0 # one-way mode
        }
        return self.http_request(endpoint, method, params, "Order")   
    
    def http_request(self, endpoint, method, params, info):
        try:
            httpClient = requests.Session()
            global time_stamp
            time_stamp = str(int(time.time() * 10 ** 3))
            payload = json.dumps(params)
            signature = self.genSignature(payload)
            headers = {
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-SIGN': signature,
                'X-BAPI-SIGN-TYPE': '2',
                'X-BAPI-TIMESTAMP': time_stamp,
                'X-BAPI-RECV-WINDOW': self.recv_window,
                'Content-Type': 'application/json'
            }
            if method == "POST":
                response = httpClient.request(method, self.url + endpoint, headers=headers, data=payload)
            else:
                payload = urlencode(params)
                response = httpClient.request(method, self.url + endpoint + '?' + payload, headers=headers)

            if response.status_code == 200:
                if response.text:
                    response_data = response.json()
                    summary = f"{info} succeeded. Elapsed Time: {response.elapsed}, Result: {response_data}"
                else:
                    summary = f"{info} succeeded. Elapsed Time: {response.elapsed}, Result: No response data"
            else:
                if response.text:
                    response_data = response.json()
                    summary = f"{info} failed. Elapsed Time: {response.elapsed}, Error: {response_data}"
                else:
                    summary = f"{info} failed. Elapsed Time: {response.elapsed}, Result: No response data"

            self.logger().info(summary)
            self.discord_notifier.notify(summary)
            print(summary)
            return True

        except Exception as e:
            self.logger().error(f"An exception occurred: {e}")
            print(f"{info} failed. An exception occurred: {e}")
            return False


    def get_best_bid_ask_price(self, symbol, side):
        order_book = self.exchange.fetch_order_book(symbol)
        if side == 'buy':
            return order_book['bids'][0][0]
        else:
            return order_book['ask'][0][0]
        
    def set_position_mode(self, mode):
        endpoint = "/v5/position/switch-mode"
        method = "POST"
        params = {
            "category": "linear",
            "symbol": "BTCUSDT",
            "coin": "USDT",
            "mode": mode  # Position mode. 0: Merged Single. 3: Both Sides
        }
        response = self.http_request(endpoint, method, params, "Set Position Mode")
        return response
        
    def check_balance(self):
        self.account.get_balance()

    def genSignature(self, payload):
        param_str= str(time_stamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        signature = hash.hexdigest()
        return signature
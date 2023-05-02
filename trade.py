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
from logger import Logger

class Trade:
    def __init__(self, config):
        self.api_key = config.get("exchange", "api_key")
        self.secret_key = config.get("exchange", "secret_key")
        self.exchange_name = config.get("exchange", "exchange_name")

        # Initialize exchange
        self.exchange = getattr(ccxt, self.exchange_name)({
            "apiKey": self.api_key,
            "secret": self.secret_key,
            "enableRateLimit": True,
        })

        self.logger = Logger("main")
        self.recv_window=str(5000)
        self.url="https://api.bybit.com"
        # self.url="https://api-testnet.bybit.com" 

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
        self.get_balance()
        # Execute trade based on prediction here
        position_manager = PositionManager(self.exchange, symbol)
        long_positions, short_positions = position_manager.separate_positions_by_side()

        symbol = "BTC/USDT"
        amount = 0.001        
        result = None

        trade_action = self.decide_trade_action(long_positions, short_positions, prediction)
        print(trade_action)

        if trade_action == "BUY_TO_OPEN":
            result = self.place_order(symbol, "Buy", amount)
        elif trade_action == "SELL_TO_OPEN":
            result = self.place_order(symbol, "Sell", amount)
        elif trade_action == "SELL_TO_CLOSE":
            result = self.place_order(symbol, "Sell", amount)
        elif trade_action == "BUY_TO_CLOSE":
            result = self.place_order(symbol, "Buy", amount)
        elif trade_action == "HOLD_LONG" or trade_action == "HOLD_SHORT" or trade_action == "DO_NOTHING":
            pass

        return result
    
    def decide_trade_action(self, long_positions, short_positions, prediction):
        if long_positions:
            if prediction == 1:
                return "HOLD_LONG"
            else:
                return "SELL_TO_CLOSE"
        else:
            if prediction == 1:
                return "BUY_TO_OPEN"
            else:
                pass

        if short_positions:
            if prediction != 1:
                return "HOLD_SHORT"
            else:
                return "BUY_TO_CLOSE"
        else:
            if prediction != 1:
                return "SELL_TO_OPEN"
            else:
                pass

        return "DO_NOTHING"
    
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

            response_data = response.json()

            if response.status_code == 200:
                summary = f"{info} succeeded. Elapsed Time: {response.elapsed}, Result: {response_data}"
            else:
                summary = f"{info} failed. Elapsed Time: {response.elapsed}, Error: {response_data}"

            print(summary)
            return summary

        except Exception as e:
            self.logger().error(f"An exception occurred: {e}")
            return f"{info} failed. An exception occurred: {e}"


    def get_best_bid_ask_price(self, symbol, side):
        order_book = self.exchange.fetch_order_book(symbol)
        if side == 'buy':
            return order_book['bids'][0][0]
        else:
            return order_book['ask'][0][0]
        
    def get_balance(self):
        balance = self.exchange.fetch_balance()
        usdt_balance = balance['total']['USDT']
        print(f'USDT balance: {usdt_balance}')

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
            print(response.text)
            print(info + " Elapsed Time : " + str(response.elapsed))
            return True
        
        except Exception as e:
            self.logger().error(f"An exception occurred: {e}")
            return False

    def genSignature(self, payload):
        param_str= str(time_stamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.secret_key, "utf-8"), param_str.encode("utf-8"),hashlib.sha256)
        signature = hash.hexdigest()
        return signature
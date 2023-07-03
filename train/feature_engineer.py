import numpy as np
import talib

class FeatureEngineer:
    def __init__(self, df):
        self.df = df
        print(df)

    def log_transform_feature(self, X):
        X[X <= 0] = np.finfo(float).eps
        return np.log(X)
    
    def calc_rank_correlation(self, series):
        n = len(series)
        ranks = series.rank()
        sum_diffs_squared = sum((ranks - np.arange(n) - 1) ** 2)
        return 1 - 6 * sum_diffs_squared / (n * (n ** 2 - 1))

    def feature_engineering(self, df):
        open = df['open'].values
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        # volume = df['volume'].values
        hilo = (high + low) / 2

        df['RSI8'] = talib.RSI(close, timeperiod=8) # default = 14
        df['RSI14'] = talib.RSI(close, timeperiod=14)
        df['RSI_ST'] = talib.RSI(close)/close
        df['RSI_LOG'] = self.log_transform_feature(talib.RSI(close))
        df['MACD'], _, _ = talib.MACD(close)
        df['MACD_ST'], _, _ = talib.MACD(close)/close
        df['ATR'] = talib.ATR(high, low, close)
        
        df['ADX'] = talib.ADX(high, low, close, timeperiod=14)
        df['ADXR'] = talib.ADXR(high, low, close, timeperiod=14)
        df['+DI'] = talib.PLUS_DI(high, low, close, timeperiod=14)
        df['-DI'] = talib.MINUS_DI(high, low, close, timeperiod=14)
        
        df['SMA15'] = talib.SMA(close, timeperiod=15) # 15分足
        df['SMA300'] = talib.SMA(close, timeperiod=300) # 15分足20MA
        
        df['BB_UPPER'], df['BB_MIDDLE'], df['BB_LOWER'] = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df['BBANDS_upperband'] = (df['BB_UPPER'] - hilo) / close
        df['BBANDS_middleband'] = (df['BB_MIDDLE'] - hilo) / close
        df['BBANDS_lowerband'] = (df['BB_LOWER'] - hilo) / close

        df['STOCH_K'], df['STOCH_D'] = talib.STOCH(high, low, close)/close
        df['MON'] = talib.MOM(close, timeperiod=5)

        df['pinbar'] = self.pinbar(df)
        df['RCI'] = df['close'].rolling(9).apply(self.calc_rank_correlation)

        df = df.fillna(method='ffill')
        df = df.fillna(method='bfill')

        print(df)

        return df

    def pinbar(self, df):
        body = np.abs(df['close'] - df['open'])
        upper_wick = df['high'] - np.max(df[['open', 'close']], axis=1)
        lower_wick = np.min(df[['open', 'close']], axis=1) - df['low']
        total_length = df['high'] - df['low']
        
        # 上向きのピンバー（ロングサイン）:下ワックが本体の3倍以上、上ワックが全体の長さの20~30%以内
        is_bullish_pinbar = (lower_wick >= 3 * body) & (upper_wick <= total_length * 0.3)
        
        # 下向きのピンバー（ショートサイン）:上ワックが本体の3倍以上、下ワックが全体の長さの20~30%以内
        is_bearish_pinbar = (upper_wick >= 3 * body) & (lower_wick <= total_length * 0.3)
        
        # 上向きピンバー = 1、下向きピンバー = 2、ピンバーでない = 0
        return np.where(is_bullish_pinbar, 1, np.where(is_bearish_pinbar, 2, 0))



import pickle
import pandas as pd
import numpy as np
import talib

class Predictor:
    def __init__(self, config):
        self.model_path = config.get("model", "model_path")

        # Load model
        with open(self.model_path, "rb") as f:
            self.model = pickle.load(f)

    def preprocess_market_data(self, dfs):
        processed_dfs = []
        for df in dfs:
            prefix = df.columns[0].split('_')[0]
            processed_df = feature_engineering(df, prefix)
            processed_df = create_label(processed_df, prefix)
            # Resample to 1m timeframe
            df_resampled = processed_df.resample('1T').asfreq()
            # Forward-fill NaN values
            df_resampled = df_resampled.fillna(method='ffill')
            processed_dfs.append(df_resampled)

        combined_df = pd.concat(processed_dfs, axis=1).fillna(0)

        # add feature support and resistance
        combined_df = support_resistance(combined_df, "1m")
        combined_df = support_resistance(combined_df, "5m")
        combined_df = support_resistance(combined_df, "15m")
        combined_df = support_resistance(combined_df, "30m")
        combined_df = price_relation(combined_df, '1m', '5m')
        combined_df = price_relation(combined_df, '5m', '15m')
        combined_df = price_relation(combined_df, '5m', '30m')

        return combined_df
    
    def predict(self, data_row):
        if "5m_target" in data_row.index:
            data_row = data_row.drop("5m_target")

        # Reshape the data_row into the correct format
        data_row = data_row.values.reshape(1, -1)
        prediction_proba = self.model.predict(data_row)
        predicted_class = [1 if prob > 0.5 else 0 for prob in prediction_proba]

        return predicted_class[0]

# feature engineering
def create_label(df, prefix, lookbehind=1):
    df[f'{prefix}_target'] = (df[f'{prefix}_close'] > df[f'{prefix}_close'].shift(lookbehind)).astype(int)
    df = df.fillna(method='ffill')
    return df

def log_transform_feature(X):
    X[X <= 0] = np.finfo(float).eps
    return np.log(X)

def support_resistance(df, prefix, window=200):
    high = df[f'{prefix}_high']
    low = df[f'{prefix}_low']
    df[f'{prefix}_support'] = low.rolling(window=window, min_periods=1).min()
    df[f'{prefix}_resistance'] = high.rolling(window=window, min_periods=1).max()
    return df

def price_relation(df, short_prefix, long_prefix):
    short_close = df[f'{short_prefix}_close']
    long_support = df[f'{long_prefix}_support']
    long_resistance = df[f'{long_prefix}_resistance']
    df[f'{short_prefix}_close_to_{long_prefix}_support'] = (short_close - long_support) / long_support
    df[f'{short_prefix}_close_to_{long_prefix}_resistance'] = (short_close - long_resistance) / long_resistance
    return df

def feature_engineering(df, prefix):
    open = df[f'{prefix}_open'].values
    high = df[f'{prefix}_high'].values
    low = df[f'{prefix}_low'].values
    close = df[f'{prefix}_close'].values
    volume = df[f'{prefix}_volume'].values
    hilo = (high + low) / 2

    df[f'{prefix}_RSI_ST'] = talib.RSI(close)/close
    df[f'{prefix}_RSI_LOG'] = log_transform_feature(talib.RSI(close))
    df[f'{prefix}_MACD'], _, _ = talib.MACD(close)
    df[f'{prefix}_MACD_ST'], _, _ = talib.MACD(close)/close
    df[f'{prefix}_ATR'] = talib.ATR(high, low, close)
    df[f'{prefix}_ADX'] = talib.ADX(high, low, close, timeperiod=14)
    df[f'{prefix}_ADXR'] = talib.ADXR(high, low, close, timeperiod=14)
    
    df[f'{prefix}_SMA20'] = talib.SMA(close, timeperiod=20)
    df[f'{prefix}_SMA50'] = talib.SMA(close, timeperiod=50)
    df[f'{prefix}_SMA200'] = talib.SMA(close, timeperiod=200)
    
    df[f'{prefix}_BB_UPPER'], df[f'{prefix}_BB_MIDDLE'], df[f'{prefix}_BB_LOWER'] = talib.BBANDS(close)
    df[f'{prefix}_BBANDS_upperband'] = (df[f'{prefix}_BB_UPPER'] - hilo) / close
    df[f'{prefix}_BBANDS_middleband'] = (df[f'{prefix}_BB_MIDDLE'] - hilo) / close
    df[f'{prefix}_BBANDS_lowerband'] = (df[f'{prefix}_BB_LOWER'] - hilo) / close
    df[f'{prefix}_STOCH_K'], df[f'{prefix}_STOCH_D'] = talib.STOCH(high, low, close)/close
    df[f'{prefix}_MON'] = talib.MOM(close, timeperiod=5)
    df[f'{prefix}_OBV'] = talib.OBV(close, volume)

    df = df.fillna(method='ffill')

    return df
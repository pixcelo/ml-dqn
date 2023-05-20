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
            processed_df = create_label(processed_df, prefix, 1)
            processed_dfs.append(processed_df)

        combined_df = pd.concat(processed_dfs, axis=1).dropna()
        # add feature support and resistance
        combined_df = support_resistance(combined_df, "1m")
        combined_df = support_resistance(combined_df, "5m")
        combined_df = support_resistance(combined_df, "15m")
        combined_df = support_resistance(combined_df, "30m")
        combined_df = support_resistance(combined_df, "1h")
        combined_df = support_resistance(combined_df, "4h")
        combined_df = support_resistance(combined_df, "1d")
        # combined_df = price_relation(combined_df, '1m', '5m')
        # combined_df = price_relation(combined_df, '1m', '15m')
        combined_df = price_relation(combined_df, '15m', '30m')
        combined_df = price_relation(combined_df, '15m', '1h')
        combined_df = price_relation(combined_df, '15m', '4h')
        combined_df = price_relation(combined_df, '15m', '1d')
        return combined_df
    
    def predict(self, market_data):
        # Preprocess market_data
        preprocessed_data = self.preprocess_market_data(market_data)

        # Print the latest close value from the market_data DataFrame
        latest_close_value = preprocessed_data.loc[0, '1m_close']
        print(f"Latest close value: {latest_close_value}")

        # Make prediction based on preprocessed market_data
        preprocessed_data = preprocessed_data.drop("15m_target", axis=1)
        prediction_proba = self.model.predict(preprocessed_data)

        # Get the predicted class
        predicted_class = np.argmax(prediction_proba, axis=1)

        return predicted_class[0]

# feature engineering
def create_label(df, prefix, lookbehind=1, lookback_window=200):
    price_changes = df[f'{prefix}_close'] - df[f'{prefix}_close'].shift(lookbehind)
    
    # Calculate mean and std for the specified lookback_window
    mean_price_change = price_changes.rolling(window=lookback_window).mean()
    std_price_change = price_changes.rolling(window=lookback_window).std()

    # Set the threshold to consider as "unchanged" (e.g., mean ±1 standard deviation)
    threshold_lower = mean_price_change - std_price_change
    threshold_upper = mean_price_change + std_price_change

    def classify_price_change(price_change, lower, upper):
        if price_change > upper:
            return 1  # up
        elif price_change < lower:
            return 2  # down
        else:
            return 0  # unchanged

    # Apply classify_price_change to each row with the corresponding thresholds
    df[f'{prefix}_target'] = np.vectorize(classify_price_change)(
        price_changes, threshold_lower, threshold_upper
    )
    df = df.dropna()
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
    # open = df[f'{prefix}_open'].values
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
    
    df[f'{prefix}_SMA10'] = talib.SMA(close, timeperiod=10)
    df[f'{prefix}_SMA50'] = talib.SMA(close, timeperiod=50)
    df[f'{prefix}_SMA200'] = talib.SMA(close, timeperiod=200)
    
    df[f'{prefix}_BB_UPPER'], df[f'{prefix}_BB_MIDDLE'], df[f'{prefix}_BB_LOWER'] = talib.BBANDS(close)
    df[f'{prefix}_BBANDS_upperband'] = (df[f'{prefix}_BB_UPPER'] - hilo) / close
    df[f'{prefix}_BBANDS_middleband'] = (df[f'{prefix}_BB_MIDDLE'] - hilo) / close
    df[f'{prefix}_BBANDS_lowerband'] = (df[f'{prefix}_BB_LOWER'] - hilo) / close
    df[f'{prefix}_STOCH_K'], df[f'{prefix}_STOCH_D'] = talib.STOCH(high, low, close)/close
    df[f'{prefix}_MON'] = talib.MOM(close, timeperiod=5)
    df[f'{prefix}_OBV'] = talib.OBV(close, volume)
    df[f'{prefix}_High_Close_Comparison'] = calculate_high_close_comparison(df, prefix)
    df[f'{prefix}_consecutive_up'], df[f'{prefix}_consecutive_down']  = calculate_consecutive_candles(df, prefix)
    df[f'{prefix}_double_top'], df[f'{prefix}_double_bottom'] = detect_double_top_bottom(df, prefix)
    df = detect_triangle_pattern(df, prefix)
    df = parallel_channel(df, prefix)
    df = add_additional_features(df, prefix)

    df = df.dropna()
    df = df.reset_index(drop=True)

    return df

def add_additional_features(df, prefix):
    close = df[f'{prefix}_close'].values
    df[f'{prefix}_PPO'] = talib.PPO(close, fastperiod=12, slowperiod=26, matype=0)
    df[f'{prefix}_perc_from_high'] = (df[f'{prefix}_high'].rolling(window=14).max() - close) / close
    df[f'{prefix}_perc_from_low'] = (close - df[f'{prefix}_low'].rolling(window=14).min()) / close    
    df[f'{prefix}_Range'] = df[f'{prefix}_high'] - df[f'{prefix}_low']
    return df

def calculate_high_close_comparison(df, prefix):
    high = df[f'{prefix}_high'].values
    close = df[f'{prefix}_close'].values
    higher_high = np.zeros(len(high), dtype=int)
    higher_close = np.zeros(len(close), dtype=int)
    higher_high[1:] = high[1:] > high[:-1]
    higher_close[1:] = close[1:] > close[:-1]
    high_close_comparison = higher_high & higher_close
    return high_close_comparison

def calculate_consecutive_candles(df, prefix):
    close = df[f'{prefix}_close'].values

    consecutive_up = np.zeros_like(close, dtype=int)
    consecutive_down = np.zeros_like(close, dtype=int)

    for i in range(1, len(close)):
        if close[i] > close[i - 1]:
            consecutive_up[i] = consecutive_up[i - 1] + 1
            consecutive_down[i] = 0
        elif close[i] < close[i - 1]:
            consecutive_up[i] = 0
            consecutive_down[i] = consecutive_down[i - 1] + 1
        else:
            consecutive_up[i] = 0
            consecutive_down[i] = 0

    return consecutive_up, consecutive_down


def detect_double_top_bottom(df, prefix, window=5, tolerance=0.03):
    double_top = np.zeros(len(df), dtype=int)
    double_bottom = np.zeros(len(df), dtype=int)

    close = df[f'{prefix}_close'].values
    close_ext = np.pad(close, (window, window), mode='edge')

    for i in range(window, len(df) - window):
        considered_range = close_ext[i:i + window * 2 + 1]
        max_index = np.argmax(considered_range)
        min_index = np.argmin(considered_range)

        if max_index == window:
            max_left = np.max(considered_range[:window])
            max_right = np.max(considered_range[window + 1:])
            max_avg = (max_left + max_right) / 2

            if np.abs(considered_range[window] - max_avg) / considered_range[window] <= tolerance:
                double_top[i] = 1

        if min_index == window:
            min_left = np.min(considered_range[:window])
            min_right = np.min(considered_range[window + 1:])
            min_avg = (min_left + min_right) / 2

            if np.abs(considered_range[window] - min_avg) / considered_range[window] <= tolerance:
                double_bottom[i] = 1

    return double_top, double_bottom


def detect_triangle_pattern(df, prefix, window=20):
    high = df[f'{prefix}_high']
    low = df[f'{prefix}_low']
    close = df[f'{prefix}_close']

    # Calculate ascending trendline
    df[f'{prefix}_ascending_trendline'] = (
        low.rolling(window=window, min_periods=1).min()
        + (high.rolling(window=window, min_periods=1).max()
        - low.rolling(window=window, min_periods=1).min()) * np.arange(1, len(df) + 1) / window
    )

    # Calculate descending trendline
    df[f'{prefix}_descending_trendline'] = (
        high.rolling(window=window, min_periods=1).max()
        - (high.rolling(window=window, min_periods=1).max()
        - low.rolling(window=window, min_periods=1).min()) * np.arange(1, len(df) + 1) / window
    )

    # Check if close price is between the trendlines
    df[f'{prefix}_triangle_pattern'] = np.where(
        (close > df[f'{prefix}_ascending_trendline']) 
        & (close < df[f'{prefix}_descending_trendline']), 1, 0
    )

    return df


def parallel_channel(df, prefix, window=20, tolerance=0.03):
    high = df[f'{prefix}_high']
    low = df[f'{prefix}_low']
    close = df[f'{prefix}_close']

    # Calculate the moving averages for the high and low prices
    high_mavg = high.rolling(window=window).mean()
    low_mavg = low.rolling(window=window).mean()

    # Calculate the channel's upper and lower boundaries
    channel_upper = high_mavg + (high_mavg - low_mavg) * tolerance
    channel_lower = low_mavg - (high_mavg - low_mavg) * tolerance

    # Add the channel boundaries to the DataFrame
    df[f'{prefix}_channel_upper'] = channel_upper
    df[f'{prefix}_channel_lower'] = channel_lower

    # Check if the price is close to the channel boundaries
    close_to_upper = abs(close - channel_upper) <= (tolerance * close)
    close_to_lower = abs(close - channel_lower) <= (tolerance * close)

    # Check if the price bounces from the channel boundaries
    bounce_from_upper = (close_to_upper.shift(1)) & (close < close.shift(1))
    bounce_from_lower = (close_to_lower.shift(1)) & (close > close.shift(1))

    # Add the bounce features to the DataFrame
    df[f'{prefix}_bounce_from_channel_upper'] = bounce_from_upper.astype(int)
    df[f'{prefix}_bounce_from_channel_lower'] = bounce_from_lower.astype(int)

    return df
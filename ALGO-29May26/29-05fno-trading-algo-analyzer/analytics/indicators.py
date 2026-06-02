import pandas as pd
import numpy as np

class IndicatorEngine:
    """
    Pure mathematical functions for calculating technical indicators.
    Side-effect free: no API calls, no prints, pure data-in data-out.
    Acts as the Single Source of Truth for math in the platform.
    """
    
    @staticmethod
    def compute_all(df: pd.DataFrame) -> pd.DataFrame:
        """Helper to compute standard layers all at once"""
        df = IndicatorEngine.add_vwap(df)
        df = IndicatorEngine.add_ema(df, period=9)
        df = IndicatorEngine.add_ema(df, period=21)
        df = IndicatorEngine.add_rsi(df, period=14)
        df = IndicatorEngine.add_bollinger_bands(df, period=20)
        df = IndicatorEngine.add_adx(df, period=14)
        df = IndicatorEngine.add_atr(df, period=14)
        df = IndicatorEngine.add_volume_metrics(df, period=20)
        return df

    @staticmethod
    def add_rsi(df: pd.DataFrame, column: str = 'close', period: int = 14) -> pd.DataFrame:
        if df.empty or len(df) < period:
            df['rsi'] = np.nan
            return df
            
        delta = df[column].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or 'volume' not in df.columns:
            df['vwap'] = np.nan
            return df
        
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return df
        
    @staticmethod
    def add_ema(df: pd.DataFrame, column: str = 'close', period: int = 9) -> pd.DataFrame:
        if df.empty:
            df[f'ema_{period}'] = np.nan
            return df
        df[f'ema_{period}'] = df[column].ewm(span=period, adjust=False).mean()
        return df

    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, column: str = 'close', period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        if df.empty or len(df) < period:
            df['bb_upper'] = np.nan
            df['bb_lower'] = np.nan
            df['bb_mid'] = np.nan
            return df
            
        df['bb_mid'] = df[column].rolling(window=period).mean()
        df['bb_std'] = df[column].rolling(window=period).std()
        df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * std_dev)
        return df

    @staticmethod
    def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        if df.empty or len(df) < period:
            df['adx'] = np.nan
            return df
        
        high_diff = df['high'].diff()
        low_diff = df['low'].diff()
        
        df['+dm'] = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
        df['-dm'] = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
        
        tr1 = pd.DataFrame(df['high'] - df['low'])
        tr2 = pd.DataFrame(abs(df['high'] - df['close'].shift(1)))
        tr3 = pd.DataFrame(abs(df['low'] - df['close'].shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        
        # Avoid division by zero
        atr = atr.replace(0, np.nan)
        
        plus_di = 100 * (df['+dm'].rolling(window=period).mean() / atr)
        minus_di = 100 * (df['-dm'].rolling(window=period).mean() / atr)
        dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
        df['adx'] = dx.rolling(window=period).mean()
        
        return df
        
    @staticmethod
    def add_volume_metrics(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        if df.empty or 'volume' not in df.columns:
            df['vol_ema'] = np.nan
            df['vol_acceleration'] = np.nan
            return df
            
        df[f'vol_ema_{period}'] = df['volume'].ewm(span=period, adjust=False).mean()
        
        # Acceleration = Rate of change of volume
        df['vol_acceleration'] = df['volume'].pct_change()
        return df

    @staticmethod
    def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Average True Range for volatility intelligence and premium expansion."""
        if df.empty or len(df) < period:
            df['atr'] = np.nan
            return df
            
        tr1 = pd.DataFrame(df['high'] - df['low'])
        tr2 = pd.DataFrame(abs(df['high'] - df['close'].shift(1)))
        tr3 = pd.DataFrame(abs(df['low'] - df['close'].shift(1)))
        frames = [tr1, tr2, tr3]
        tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
        
        df['atr'] = tr.rolling(window=period).mean()
        return df

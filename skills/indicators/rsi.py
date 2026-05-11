import pandas as pd

def calculate_rsi(df: pd.DataFrame, period: int = 14, price_col: str = "close") -> pd.DataFrame:
    """
    Pandas DataFrame을 받아 지정된 기간(period)의 RSI(상대강도지수)를 계산하여 컬럼에 추가하는 순수 함수.
    외부 라이브러리(TA-Lib 등) 의존성을 제거하고 Pandas만으로 구현하여 이식성 극대화.
    """
    # 원본 보호를 위해 복사본 사용
    result_df = df.copy()
    
    delta = result_df[price_col].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    # 단순 이동평균(SMA) 방식 적용 (필요에 따라 지수이동평균 EMA로 변경 가능)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss
    result_df['rsi'] = 100 - (100 / (1 + rs))
    
    return result_df

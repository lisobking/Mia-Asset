def calculate_position_size(total_capital: float, risk_percentage: float = 0.5) -> float:
    """
    MVP 기준: 한 번 진입 시 최대 허용 비중 계산.
    예: 전체 시드 $10,000 * 0.5 (50%) = $5,000만 진입
    """
    return total_capital * risk_percentage

def check_stop_condition(entry_price: float, current_price: float, highest_price: float, 
                         stop_loss_pct: float = 0.02, trailing_pct: float = 0.015) -> str:
    """
    현재 가격이 절대 손절(-2%) 또는 트레일링 스탑(-1.5%) 라인을 터치했는지 확인.
    반환값: "HOLD", "STOP_LOSS", "TRAILING_STOP"
    """
    # 1. 절대 손절 라인 터치 (최우선순위)
    if current_price <= entry_price * (1 - stop_loss_pct):
        return "STOP_LOSS"
        
    # 2. 트레일링 스탑 적용 (수익 달성 이후 고점 대비 일정 비율 하락 시)
    # (여기서는 고점이 이미 진입가보다 충분히 높다고 전제함)
    if current_price <= highest_price * (1 - trailing_pct):
        return "TRAILING_STOP"
        
    return "HOLD"

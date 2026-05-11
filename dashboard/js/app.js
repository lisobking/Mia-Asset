// UI Interaction 및 FastAPI 연동
document.addEventListener('DOMContentLoaded', () => {
    const priceEl = document.getElementById('current-price');
    const balanceEl = document.getElementById('current-balance');
    const rsiFill = document.getElementById('rsi-fill');
    const rsiVal = document.getElementById('rsi-val');
    const stateBadge = document.getElementById('bot-state-badge');
    const stateDesc = document.getElementById('bot-state-desc');
    
    // 2초마다 백엔드 API에서 봇 상태를 가져와 대시보드 업데이트
    setInterval(async () => {
        try {
            const token = localStorage.getItem("agbot_token");
            if (!token) return; // 로그인 안됨
            
            const response = await fetch('/api/status', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    localStorage.removeItem("agbot_token");
                    window.location.href = "login.html";
                }
                return;
            }
            
            const data = await response.json();
            
            // 1. 가격 업데이트 및 변동 효과
            const oldPrice = parseFloat(priceEl.innerText) || 0;
            const newPrice = data.current_price || 0;
            priceEl.innerText = newPrice.toFixed(2);
            
            if(newPrice > oldPrice && oldPrice > 0) {
                priceEl.style.color = '#00ff88';
            } else if (newPrice < oldPrice && oldPrice > 0) {
                priceEl.style.color = '#ff3366';
            }
            setTimeout(() => { priceEl.style.color = 'inherit'; }, 500);

            // 잔고 업데이트
            if (balanceEl && data.balance !== undefined) {
                balanceEl.innerText = data.balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            }

            // 2. RSI 업데이트
            if (rsiVal && rsiFill) {
                const rsi = data.rsi_15m || 0;
                rsiVal.innerText = rsi.toFixed(1);
                rsiFill.style.width = `${Math.min(Math.max(rsi, 0), 100)}%`;
            }
            
            // 3. 상태(State) 뱃지 업데이트
            if (stateBadge && data.state) {
                if (data.state === "IDLE") {
                    stateBadge.className = "current-state";
                    stateBadge.innerText = "대기중 ☕";
                    stateBadge.style.color = "#8b92a5";
                    stateBadge.style.background = "rgba(255,255,255,0.05)";
                    if (stateDesc) stateDesc.innerText = "현재 좋은 매수 타이밍을 기다리고 있습니다.";
                } else if (data.state === "HOLDING") {
                    stateBadge.className = "current-state badge-holding";
                    stateBadge.innerText = "주식 보유중 📈";
                    stateBadge.style.color = "#00ff88";
                    stateBadge.style.background = "rgba(0, 255, 136, 0.1)";
                    if (stateDesc) stateDesc.innerText = "현재 수익을 지켜보며 매도 타이밍을 찾고 있어요.";
                }
            }

        } catch (error) {
            console.error("API 연동 에러:", error);
        }
    }, 2000);
});

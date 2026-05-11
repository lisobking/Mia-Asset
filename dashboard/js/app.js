// UI Interaction 및 FastAPI 연동
document.addEventListener('DOMContentLoaded', () => {
    const priceEl = document.getElementById('current-price');
    const balanceEl = document.getElementById('current-balance');
    const balanceKrwEl = document.getElementById('balance-krw');
    const rsiFill = document.getElementById('rsi-fill');
    const rsiVal = document.getElementById('rsi-val');
    const rsiDisplayArea = document.getElementById('rsi-display-area');
    const rsiLoading = document.getElementById('rsi-loading');
    const stateBadge = document.getElementById('bot-state-badge');
    const stateDesc = document.getElementById('bot-state-desc');
    let isHidden = false;

    // 자산 가리기/보기 토글
    const toggleBtn = document.getElementById('toggle-visibility');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            isHidden = !isHidden;
            toggleBtn.innerText = isHidden ? '🙈' : '👁️';
            if (balanceEl) balanceEl.innerText = isHidden ? '****' : (lastBalance.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}));
            if (balanceKrwEl) balanceKrwEl.innerText = isHidden ? '≈ ₩****' : `≈ ₩${Math.round(lastBalance * lastUsdKrw).toLocaleString('ko-KR')}`;
        });
    }

    let lastBalance = 0;
    let lastUsdKrw = 1380;

    // 자동매매 기준금액 슬라이더
    const slider = document.getElementById('base-amount-slider');
    const sliderDisplay = document.getElementById('base-amount-display');
    let sliderSaveTimer = null;

    function updateSliderDisplay(val, krwRate) {
        const krw = Math.round(val * krwRate);
        if (sliderDisplay) sliderDisplay.innerText = `$${parseInt(val).toLocaleString('en-US')} (≈ ₩${krw.toLocaleString('ko-KR')})`;
    }

    if (slider) {
        slider.addEventListener('input', (e) => {
            updateSliderDisplay(e.target.value, lastUsdKrw);
        });
        slider.addEventListener('change', async (e) => {
            // 슬라이더 변경 완료 시 백엔드 저장
            clearTimeout(sliderSaveTimer);
            sliderSaveTimer = setTimeout(async () => {
                const token = localStorage.getItem("agbot_token");
                if (!token) return;
                try {
                    const symEl = document.getElementById('market-card-title');
                    const sym = symEl ? symEl.innerText.replace('지금 ', '').replace(' 주가는?', '') : 'SOXL';
                    await fetch('/api/trading-settings', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json','Authorization':`Bearer ${token}`},
                        body: JSON.stringify({target_symbol: sym, trade_amount: parseFloat(e.target.value)})
                    });
                } catch(err) { console.error('슬라이더 저장 실패:', err); }
            }, 800);
        });
    }

    // 관리자 버튼
    const adminBtn = document.getElementById("admin-btn");
    if (adminBtn) {
        adminBtn.addEventListener("click", async () => {
            const token = localStorage.getItem("agbot_token");
            try {
                const res = await fetch("/api/admin/users", { headers: { 'Authorization': `Bearer ${token}` } });
                if (res.ok) {
                    const users = await res.json();
                    alert(`👑 가입자 현황 (총 ${users.length}명)\n\n${users.map(u => `- ${u.email}`).join("\n")}`);
                } else { alert("권한이 없습니다."); }
            } catch (e) { alert("서버 연결 오류"); }
        });
    }

    // 자동매매 시작/정지
    async function toggleBot(isActive) {
        const token = localStorage.getItem("agbot_token");
        if (!token) return;
        try {
            const res = await fetch("/api/bot/toggle", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ is_active: isActive })
            });
            const data = await res.json();
            alert(data.message);
        } catch (e) { alert("통신 오류 발생"); }
    }
    const btnStart = document.getElementById("btn-bot-start");
    const btnPause = document.getElementById("btn-bot-pause");
    if (btnStart) btnStart.addEventListener("click", () => toggleBot(true));
    if (btnPause) btnPause.addEventListener("click", () => toggleBot(false));

    // 수동 주문
    async function manualTrade(action) {
        const qtyInputId = action === 'buy' ? 'manual-buy-qty' : 'manual-sell-qty';
        const qty = parseInt(document.getElementById(qtyInputId)?.value || 0);
        if (!qty || qty <= 0) { alert("주문할 수량을 1주 이상 입력해주세요."); return; }
        if (!confirm(`정말로 즉시 ${qty}주를 ${action === 'buy' ? '매수' : '매도'}하시겠습니까?`)) return;
        const token = localStorage.getItem("agbot_token");
        if (!token) return;
        const btn = action === 'buy' ? document.getElementById("btn-manual-buy") : document.getElementById("btn-manual-sell");
        const orig = btn.innerText;
        btn.innerText = "요청중..."; btn.disabled = true;
        try {
            const res = await fetch("/api/trade", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ action, qty })
            });
            alert((await res.json()).message);
        } catch (e) { alert("통신 오류 발생"); }
        btn.innerText = orig; btn.disabled = false;
    }
    const btnBuy = document.getElementById("btn-manual-buy");
    const btnSell = document.getElementById("btn-manual-sell");
    if (btnBuy) btnBuy.addEventListener("click", () => manualTrade("buy"));
    if (btnSell) btnSell.addEventListener("click", () => manualTrade("sell"));

    // 상태 갱신 핵심 함수
    const refreshBtn = document.getElementById("btn-refresh-price");
    const lastUpdatedEl = document.getElementById("last-updated");
    let countdown = 15;

    async function fetchStatus() {
        const token = localStorage.getItem("agbot_token");
        if (!token) return;
        if (refreshBtn) { refreshBtn.innerHTML = '⏳ <span style="font-size:0.8rem;">불러오는 중...</span>'; refreshBtn.disabled = true; }
        try {
            const response = await fetch('/api/status', { headers: { 'Authorization': `Bearer ${token}` } });
            if (!response.ok) {
                if (response.status === 401) { localStorage.removeItem("agbot_token"); window.location.href = "login.html"; }
                return;
            }
            const data = await response.json();

            // 관리자 버튼
            if (data.email === "lisob@naver.com") {
                const ab = document.getElementById("admin-btn");
                if (ab) ab.style.display = "inline-block";
            }

            lastUsdKrw = data.usd_krw || 1380;

            // 1. 주가 (달러 + 원화)
            const oldPrice = parseFloat(priceEl?.innerText.replace(/,/g, '')) || 0;
            const newPrice = data.current_price || 0;
            if (priceEl && newPrice > 0) {
                priceEl.innerText = newPrice.toFixed(2);
                if (newPrice > oldPrice && oldPrice > 0) { priceEl.style.color = '#00ff88'; }
                else if (newPrice < oldPrice && oldPrice > 0) { priceEl.style.color = '#ff3366'; }
                setTimeout(() => { priceEl.style.color = 'inherit'; }, 800);
                const krwPriceEl = document.getElementById('current-price-krw');
                if (krwPriceEl) krwPriceEl.innerText = `≈ ₩${Math.round(newPrice * lastUsdKrw).toLocaleString('ko-KR')}`;
                const titleEl = document.getElementById('market-card-title');
                if (titleEl && data.symbol) titleEl.innerText = `지금 ${data.symbol} 주가는?`;
            }

            // 2. 잔고 (달러 + 원화)
            lastBalance = data.balance || 0;
            if (balanceEl && !isHidden) {
                balanceEl.innerText = lastBalance.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
            }
            if (balanceKrwEl && !isHidden) {
                balanceKrwEl.innerText = `≈ ₩${Math.round(lastBalance * lastUsdKrw).toLocaleString('ko-KR')}`;
            }
            const manualBalance = document.getElementById("manual-balance");
            const manualHeldQty = document.getElementById("manual-held-qty");
            if (manualBalance) manualBalance.innerText = lastBalance.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
            if (manualHeldQty) manualHeldQty.innerText = data.held_qty || 0;

            // 3. RSI — 0이면 로딩 표시, 값 있으면 바 표시
            const rsi = data.rsi_15m || 0;
            if (rsiVal) rsiVal.innerText = rsi.toFixed(1);
            if (rsi > 0) {
                if (rsiLoading) rsiLoading.style.display = 'none';
                if (rsiDisplayArea) rsiDisplayArea.style.display = 'block';
                if (rsiFill) rsiFill.style.width = `${Math.min(Math.max(rsi, 0), 100)}%`;
                // RSI 색상 구분
                if (rsiFill) {
                    if (rsi <= 30) rsiFill.style.background = 'linear-gradient(90deg, #3182f6, #00f0ff)';
                    else if (rsi >= 70) rsiFill.style.background = 'linear-gradient(90deg, #ffcc00, #ff3366)';
                    else rsiFill.style.background = 'linear-gradient(90deg, #3182f6, #ff3366)';
                }
            } else {
                if (rsiLoading) rsiLoading.style.display = 'block';
                if (rsiDisplayArea) rsiDisplayArea.style.display = 'none';
            }

            // 4. 봇 상태 뱃지
            if (stateBadge && data.state) {
                if (data.is_active === false) {
                    stateBadge.innerText = "일시 정지됨 ⏸️";
                    stateBadge.style.cssText = "color:#ffcc00; background:rgba(255,204,0,0.1);";
                    if (stateDesc) stateDesc.innerText = "자동매매가 중지되었습니다. 수동매매만 가능합니다.";
                } else if (data.state === "IDLE") {
                    stateBadge.innerText = "대기중 ☕";
                    stateBadge.style.cssText = "color:#8b92a5; background:rgba(255,255,255,0.05);";
                    if (stateDesc) stateDesc.innerText = "현재 좋은 매수 타이밍을 기다리고 있습니다.";
                } else if (data.state === "HOLDING") {
                    stateBadge.innerText = "주식 보유중 📈";
                    stateBadge.style.cssText = "color:#00ff88; background:rgba(0,255,136,0.1);";
                    if (stateDesc) stateDesc.innerText = "현재 수익을 지켜보며 매도 타이밍을 찾고 있어요.";
                }
            }

            // 5. 슬라이더 동기화 (서버 저장값과 UI 동기화)
            if (data.trade_amount && slider) {
                const ta = Math.min(Math.max(data.trade_amount, 100), 500);
                slider.value = ta;
                updateSliderDisplay(ta, lastUsdKrw);
            } else {
                updateSliderDisplay(slider ? slider.value : 500, lastUsdKrw);
            }

            // 6. 마지막 갱신 시각
            const now = new Date();
            if (lastUpdatedEl) {
                lastUpdatedEl.innerText = `마지막 갱신: ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;
            }
            countdown = 30;
        } catch (err) {
            console.error("API 연동 에러:", err);
        } finally {
            if (refreshBtn) { refreshBtn.innerHTML = '🔄 <span style="font-size:0.8rem;">새로고침</span>'; refreshBtn.disabled = false; }
        }
    }

    if (refreshBtn) refreshBtn.addEventListener("click", () => { countdown = 30; fetchStatus(); });

    // 30초 자동 갱신 타이머
    setInterval(() => {
        countdown--;
        if (lastUpdatedEl && countdown > 0) {
            const base = lastUpdatedEl.innerText.split(" (")[0];
            lastUpdatedEl.innerText = `${base} (${countdown}초 후 갱신)`;
        }
        if (countdown <= 0) { countdown = 15; fetchStatus(); }
    }, 1000);

    fetchStatus();
});

// UI Interaction 및 FastAPI 연동
document.addEventListener('DOMContentLoaded', () => {
    const priceEl = document.getElementById('current-price');
    const balanceEl = document.getElementById('current-balance');
    const rsiFill = document.getElementById('rsi-fill');
    const rsiVal = document.getElementById('rsi-val');
    const stateBadge = document.getElementById('bot-state-badge');
    const stateDesc = document.getElementById('bot-state-desc');
    
    // 자산 가리기/보기 토글 기능
    const toggleBtn = document.getElementById('toggle-visibility');
    let isHidden = false;
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            isHidden = !isHidden;
            toggleBtn.innerText = isHidden ? '🙈' : '👁️';
            if (isHidden && balanceEl) {
                balanceEl.innerText = '****';
            }
        });
    }

    // 자동매매 기준금액 슬라이더 기능
    const slider = document.getElementById('base-amount-slider');
    const sliderDisplay = document.getElementById('base-amount-display');
    if (slider && sliderDisplay) {
        slider.addEventListener('input', (e) => {
            sliderDisplay.innerText = '$' + parseInt(e.target.value).toLocaleString('en-US');
            // TODO: 슬라이더 값을 백엔드(api/trading-settings)로 저장하는 API 호출 추가 가능
        });
    }

    // 관리자 버튼 클릭 이벤트
    const adminBtn = document.getElementById("admin-btn");
    if (adminBtn) {
        adminBtn.addEventListener("click", async () => {
            const token = localStorage.getItem("agbot_token");
            try {
                const res = await fetch("/api/admin/users", { headers: { 'Authorization': `Bearer ${token}` } });
                if (res.ok) {
                    const users = await res.json();
                    const userList = users.map(u => `- ${u.email}`).join("\n");
                    alert(`👑 가입자 현황 (총 ${users.length}명)\n\n${userList}`);
                } else {
                    alert("권한이 없습니다.");
                }
            } catch (e) {
                alert("서버 연결 오류");
            }
        });
    }

    // 자동매매 시작 및 정지 버튼 연동
    const btnStart = document.getElementById("btn-bot-start");
    const btnPause = document.getElementById("btn-bot-pause");
    
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
        } catch (e) {
            alert("통신 오류 발생");
        }
    }
    
    if (btnStart) btnStart.addEventListener("click", () => toggleBot(true));
    if (btnPause) btnPause.addEventListener("click", () => toggleBot(false));

    // 수동 주문 버튼 연동
    const btnBuy = document.getElementById("btn-manual-buy");
    const btnSell = document.getElementById("btn-manual-sell");

    async function manualTrade(action) {
        const qtyInputId = action === 'buy' ? 'manual-buy-qty' : 'manual-sell-qty';
        const qtyInput = document.getElementById(qtyInputId);
        const qty = parseInt(qtyInput ? qtyInput.value : 0);
        if (!qty || qty <= 0) {
            alert("주문할 수량을 1주 이상 정확히 입력해주세요.");
            return;
        }

        if (!confirm(`정말로 즉시 ${qty}주를 ${action === 'buy' ? '매수' : '매도'}하시겠습니까?`)) return;
        const token = localStorage.getItem("agbot_token");
        if (!token) return;
        
        // 버튼 로딩 상태 표시
        const btn = action === 'buy' ? btnBuy : btnSell;
        const originalText = btn.innerText;
        btn.innerText = "요청중...";
        btn.disabled = true;
        
        try {
            const res = await fetch("/api/trade", {
                method: "POST",
                headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
                body: JSON.stringify({ action: action, qty: qty })
            });
            const data = await res.json();
            alert(data.message);
        } catch (e) {
            alert("통신 오류 발생");
        }
        
        btn.innerText = originalText;
        btn.disabled = false;
    }

    if (btnBuy) btnBuy.addEventListener("click", () => manualTrade("buy"));
    if (btnSell) btnSell.addEventListener("click", () => manualTrade("sell"));

    // ── 주가 새로고침 관련 ────────────────────────────
    const refreshBtn = document.getElementById("btn-refresh-price");
    const lastUpdatedEl = document.getElementById("last-updated");
    let countdown = 30;

    // 상태 갱신 핵심 함수 (수동 + 자동 공용)
    async function fetchStatus() {
        const token = localStorage.getItem("agbot_token");
        if (!token) return;

        if (refreshBtn) {
            refreshBtn.innerHTML = '⏳ <span style="font-size:0.8rem;">불러오는 중...</span>';
            refreshBtn.disabled = true;
        }

        try {
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

            // 관리자 버튼 표시
            if (data.email === "lisob@naver.com") {
                const ab = document.getElementById("admin-btn");
                if (ab) ab.style.display = "inline-block";
            }

            // 1. 가격 업데이트 및 변동 색상 효과
            const oldPrice = parseFloat(priceEl.innerText.replace(/,/g, '')) || 0;
            const newPrice = data.current_price || 0;
            if (!isNaN(newPrice) && newPrice > 0) {
                priceEl.innerText = newPrice.toFixed(2);
                if (newPrice > oldPrice && oldPrice > 0) {
                    priceEl.style.color = '#00ff88';
                } else if (newPrice < oldPrice && oldPrice > 0) {
                    priceEl.style.color = '#ff3366';
                }
                setTimeout(() => { priceEl.style.color = 'inherit'; }, 800);
            }

            // 2. 잔고 업데이트
            if (balanceEl && data.balance !== undefined && !isHidden) {
                balanceEl.innerText = data.balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            }
            const manualBalance = document.getElementById("manual-balance");
            const manualHeldQty = document.getElementById("manual-held-qty");
            if (manualBalance) manualBalance.innerText = data.balance ? data.balance.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) : "0.00";
            if (manualHeldQty) manualHeldQty.innerText = data.held_qty || 0;

            // 3. RSI 업데이트
            if (rsiVal && rsiFill) {
                const rsi = data.rsi_15m || 0;
                rsiVal.innerText = rsi.toFixed(1);
                rsiFill.style.width = `${Math.min(Math.max(rsi, 0), 100)}%`;
            }

            // 4. 봇 상태 뱃지 업데이트
            if (stateBadge && data.state) {
                if (data.is_active === false) {
                    stateBadge.innerText = "일시 정지됨 ⏸️";
                    stateBadge.style.color = "#ffcc00";
                    stateBadge.style.background = "rgba(255,204,0,0.1)";
                    if (stateDesc) stateDesc.innerText = "자동매매가 중지되었습니다. 수동매매만 가능합니다.";
                } else if (data.state === "IDLE") {
                    stateBadge.innerText = "대기중 ☕";
                    stateBadge.style.color = "#8b92a5";
                    stateBadge.style.background = "rgba(255,255,255,0.05)";
                    if (stateDesc) stateDesc.innerText = "현재 좋은 매수 타이밍을 기다리고 있습니다.";
                } else if (data.state === "HOLDING") {
                    stateBadge.innerText = "주식 보유중 📈";
                    stateBadge.style.color = "#00ff88";
                    stateBadge.style.background = "rgba(0,255,136,0.1)";
                    if (stateDesc) stateDesc.innerText = "현재 수익을 지켜보며 매도 타이밍을 찾고 있어요.";
                }
            }

            // 5. 마지막 업데이트 시각 표시
            const now = new Date();
            if (lastUpdatedEl) {
                lastUpdatedEl.innerText = `마지막 갱신: ${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}`;
            }
            countdown = 30;

        } catch (err) {
            console.error("API 연동 에러:", err);
        } finally {
            if (refreshBtn) {
                refreshBtn.innerHTML = '🔄 <span style="font-size:0.8rem;">새로고침</span>';
                refreshBtn.disabled = false;
            }
        }
    }

    // 새로고침 버튼 클릭 시 즉시 호출
    if (refreshBtn) refreshBtn.addEventListener("click", () => {
        countdown = 30;
        fetchStatus();
    });

    // 30초 자동 갱신 타이머
    setInterval(() => {
        countdown--;
        if (lastUpdatedEl && countdown > 0) {
            const base = lastUpdatedEl.innerText.split(" (")[0];
            lastUpdatedEl.innerText = `${base} (${countdown}초 후 갱신)`;
        }
        if (countdown <= 0) {
            countdown = 30;
            fetchStatus();
        }
    }, 1000);

    // 페이지 로드 시 즉시 1회 실행
    fetchStatus();
});

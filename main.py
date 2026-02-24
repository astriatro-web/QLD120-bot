import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import requests

# 1. 환경 변수 로드
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def get_rsi(series, period=14):
    """RSI 계산"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_consecutive_days(price_series, ma_series):
    """연속 하락 일수 계산"""
    under_ma = price_series < ma_series
    count = 0
    for val in under_ma[::-1]:
        if val: count += 1
        else: break
    return count

def run_strategy():
    try:
        # 2. 데이터 다운로드
        tickers = ["USDKRW=X", "QLD", "SSO", "QQQ", "^VIX", "TQQQ"]
        raw_data = yf.download(tickers, period="3y", interval="1d", progress=False, auto_adjust=True)
        
        data = raw_data['Close'] if isinstance(raw_data.columns, pd.MultiIndex) else raw_data
            
        # 3. 주요 지표 추출
        rate = data["USDKRW=X"].dropna().iloc[-1]
        vix_now = data["^VIX"].dropna().iloc[-1]
        
        # 4. QQQ 분석
        qqq_series = data["QQQ"].dropna()
        qqq_now = qqq_series.iloc[-1]
        qqq_ma20 = qqq_series.rolling(20).mean().iloc[-1]
        qqq_ma120 = qqq_series.rolling(120).mean().iloc[-1]
        qqq_ma200 = qqq_series.rolling(200).mean().iloc[-1]
        qqq_rsi = get_rsi(qqq_series).iloc[-1]
        
        # 5. QLD 분석 (200일선 추가)
        qld_series = data["QLD"].dropna()
        qld_now = qld_series.iloc[-1]
        qld_ma60 = qld_series.rolling(60).mean().iloc[-1]
        qld_ma120_s = qld_series.rolling(120).mean()
        qld_ma120 = qld_ma120_s.iloc[-1]
        qld_ma200 = qld_series.rolling(200).mean().iloc[-1] # 추가
        qld_ma300 = qld_series.rolling(300).mean().iloc[-1]
        qld_days_120 = get_consecutive_days(qld_series, qld_ma120_s)
        
        # 6. SSO 분석 (200일선 추가)
        sso_series = data["SSO"].dropna()
        sso_now = sso_series.iloc[-1]
        sso_ma60 = sso_series.rolling(60).mean().iloc[-1]
        sso_ma120 = sso_series.rolling(120).mean().iloc[-1]
        sso_ma200 = sso_series.rolling(200).mean().iloc[-1] # 추가
        sso_ma300 = sso_series.rolling(300).mean().iloc[-1]

        # 7. 전략 신호 판독
        tqqq_signal = qqq_rsi < 35 and vix_now > 28
        
        high_bet_status = "⚠️ 금지"
        if qqq_now > qqq_ma120:
            if qqq_now < qqq_ma20 and qqq_rsi < 50:
                high_bet_status = "✅ 적극 가능 (눌림목)"
            elif qqq_now < qqq_ma20:
                high_bet_status = "🟡 보통 (분할 매수)"
            else:
                high_bet_status = "💎 관망 (추격 금지)"

        # 8. 리포트 구성
        msg = f"📊 *[QLD 전략 아침 리포트]*\n"
        msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"💵 *환율:* {rate:,.2f}원 | 🌡️ *VIX:* {vix_now:.2f}\n"
        msg += f"🧠 *Fear & Greed:* [CNN 바로가기](https://www.cnn.com/markets/fear-and-greed)\n"
        msg += f"📉 *QQQ RSI:* {qqq_rsi:.2f}\n"
        msg += f"📝 *분할 매수 금액:* [코랩 이동](https://colab.research.google.com/drive/1gqPmUIYoWnPWomINM7nQX8SvIiq9L5m1?usp=sharing)\n"
        msg += f"━━━━━━━━━━━━━━━\n\n"
        
        # QLD 상세 (순서: 60-120-200-300)
        msg += f"📍 *QLD 상세 (현재: ${qld_now:.2f})*\n"
        msg += f"- 60일선: ${qld_ma60:.2f} ({'📉하방' if qld_now < qld_ma60 else '📈상방'})\n"
        msg += f"- 120일선: ${qld_ma120:.2f} ({'📉하방' if qld_now < qld_ma120 else '📈상방'})\n"
        msg += f"- 200일선: ${qld_ma200:.2f} ({'📉하방' if qld_now < qld_ma200 else '📈상방'})\n"
        msg += f"- 300일선: ${qld_ma300:.2f} ({'📉하방' if qld_now < qld_ma300 else '📈상방'})\n"
        
        if qld_now < qld_ma120:
            msg += f"👉 *🔥 QLD 매수 구간 ({qld_days_120}일차)*\n\n"
        else:
            msg += f"👉 *💎 QLD 관망 유지*\n\n"

        # SSO 상세 (순서: 120-200-300)
        msg += f"📍 *SSO 매수 보조 (현재: ${sso_now:.2f})*\n"
        msg += f"- 120일선: ${sso_ma120:.2f} ({'📉하방' if sso_now < sso_ma120 else '📈상방'})\n"
        msg += f"- 200일선: ${sso_ma200:.2f} ({'📉하방' if sso_now < sso_ma200 else '📈상방'})\n"
        msg += f"- 300일선: ${sso_ma300:.2f} ({'📉하방' if sso_now < sso_ma300 else '📈상방'})\n\n"

        msg += f"🚀 *TQQQ 특공대 신호*\n"
        msg += f"👉 {'🔥 [강력 신호] TQQQ 진입 가능!' if tqqq_signal else '💤 신호 없음'}\n\n"

        msg += f"🛡️ *보조지표 요약*\n"
        msg += f"- QQQ 200선: {'📉 하방(위험)' if qqq_now < qqq_ma200 else '📈 상방(안정)'}\n"
        msg += f"- 고배팅 가능: {high_bet_status}\n"
        
        sso_status = "🚨익절권장" if sso_now < sso_ma60 else ("🔄재매수가능" if sso_now > sso_ma120 else "💤관망")
        msg += f"- 텐버거(SSO): {sso_status}\n"
        msg += f"━━━━━━━━━━━━━━━"

        # 9. 최종 전송
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
        requests.post(url, json=payload)

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": CHAT_ID, "text": f"❌ 시스템 에러: {str(e)}"})

if __name__ == "__main__":
    run_strategy()

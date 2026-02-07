import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import requests

# 텔레그램 설정
TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    requests.post(url, json=payload)

def get_ma_series(data, ticker, window):
    series = data[ticker].dropna()
    return series.rolling(window=window).mean()

def get_consecutive_days(price_series, ma_series):
    under_ma = price_series < ma_series
    count = 0
    for i in range(len(under_ma)-1, -1, -1):
        if under_ma.iloc[i]: count += 1
        else: break
    return count

def run_strategy():
    try:
        # 데이터 호출
        tickers = ["USDKRW=X", "QLD", "SSO", "QQQ", "^VIX"]
        data = yf.download(tickers, period="3y", interval="1d", progress=False, auto_adjust=True)['Close']
        
        rate = data["USDKRW=X"].dropna().iloc[-1]
        vix_now = data["^VIX"].dropna().iloc[-1]
        
        # QLD 데이터 및 이평선
        qld_series = data["QLD"].dropna()
        qld_now = qld_series.iloc[-1]
        qld_ma60 = get_ma_series(data, "QLD", 60).iloc[-1]
        qld_ma120_s = get_ma_series(data, "QLD", 120)
        qld_ma300_s = get_ma_series(data, "QLD", 300)
        qld_ma120, qld_ma300 = qld_ma120_s.iloc[-1], qld_ma300_s.iloc[-1]
        qld_days_120 = get_consecutive_days(qld_series, qld_ma120_s)
        
        # SSO 데이터 및 이평선
        sso_series = data["SSO"].dropna()
        sso_now = sso_series.iloc[-1]
        sso_ma60 = get_ma_series(data, "SSO", 60).iloc[-1]
        sso_ma120 = get_ma_series(data, "SSO", 120).iloc[-1]
        sso_ma300 = get_ma_series(data, "SSO", 300).iloc[-1]

        # QQQ 데이터
        qqq_now = data["QQQ"].dropna().iloc[-1]
        qqq_ma120 = get_ma_series(data, "QQQ", 120).iloc[-1]
        qqq_ma20 = get_ma_series(data, "QQQ", 20).iloc[-1]

        # 텔레그램 메시지 구성
        msg = f"📊 *[QLD 전략 아침 리포트]*\n"
        msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"💵 *환율:* {rate:,.2f}원 | 🌡️ *VIX:* {vix_now:.2f}\n"
        msg += f"🧠 *Fear & Greed:* [바로가기](https://www.cnn.com/markets/fear-and-greed)\n"
        msg += f"📝 *분할 매수 금액 및 본문:* [바로가기](https://colab.research.google.com/drive/1x0o1OMcg7L5H67-kdKSHSVbtSuQanFjN?usp=sharing)\n"
        msg += f"━━━━━━━━━━━━━━━\n\n"
        
        msg += f"📍 *QLD 상세 지표 (현재: ${qld_now:.2f})*\n"
        msg += f"- 60일선: ${qld_ma60:.2f} ({'📉하방' if qld_now < qld_ma60 else '📈상방'})\n"
        msg += f"- 120일선: ${qld_ma120:.2f} ({'📉하방' if qld_now < qld_ma120 else '📈상방'})\n"
        msg += f"- 300일선: ${qld_ma300:.2f} ({'📉하방' if qld_now < qld_ma300 else '📈상방'})\n"
        
        if qld_now < qld_ma120:
            msg += f"👉 *🔥 QLD 매수 구간 ({qld_days_120}일차)*\n\n"
        else:
            msg += f"👉 *💎 QLD 관망 유지*\n\n"

        msg += f"📍 *SSO 매수 근거 보조지표 (현재: ${sso_now:.2f})*\n"
        msg += f"- 120일선: ${sso_ma120:.2f} ({'📉하방' if sso_now < sso_ma120 else '📈상방'})\n"
        msg += f"- 300일선: ${sso_ma300:.2f} ({'📉하방' if sso_now < sso_ma300 else '📈상방'})\n\n"

        msg += f"🛡️ *보조지표 요약*\n"
        msg += f"- QQQ 120선: {'📉 하방(주의)' if qqq_now < qqq_ma120 else '📈 상방(안정)'}\n"
        msg += f"- 고배팅 가능: {'✅ 가능' if qqq_now > qqq_ma120 and qqq_now < qqq_ma20 else '⚠️ 금지'}\n"
        
        sso_status = "🚨익절권장" if sso_now < sso_ma60 else ("🔄재매수가능" if sso_now > sso_ma120 else "💤관망")
        msg += f"- 텐버거(SSO): {sso_status}\n"
        msg += f"━━━━━━━━━━━━━━━"

        send_telegram_msg(msg)
        print("Telegram message sent successfully!")

    except Exception as e:
        error_msg = f"❌ 에러 발생: {str(e)}"
        send_telegram_msg(error_msg)

if __name__ == "__main__":
    run_strategy()

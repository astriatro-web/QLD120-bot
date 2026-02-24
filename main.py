import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import requests
import numpy as np

# 1. 환경 변수 로드
TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def get_indicators(df, period=14):
    """RSI 및 ADX 계산"""
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # RSI 계산
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # ADX 계산을 위한 TR, DM 계산
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(window=period).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    
    return rsi, adx

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
        # 2. 데이터 다운로드 (ADX 계산을 위해 High, Low 포함)
        tickers = ["USDKRW=X", "QLD", "SSO", "QQQ", "^VIX", "TQQQ"]
        raw_data = yf.download(tickers, period="3y", interval="1d", progress=False, auto_adjust=True)
        
        # 3. 주요 지표 추출
        close_data = raw_data['Close']
        rate = close_data["USDKRW=X"].dropna().iloc[-1]
        vix_now = close_data["^VIX"].dropna().iloc[-1]
        
        # 4. QQQ 분석 (ADX 필터 적용)
        qqq_df = raw_data.xs('QQQ', axis=1, level=1).dropna()
        qqq_rsi_series, qqq_adx_series = get_indicators(qqq_df)
        
        qqq_now = qqq_df['Close'].iloc[-1]
        qqq_rsi = qqq_rsi_series.iloc[-1]
        qqq_adx = qqq_adx_series.iloc[-1]
        qqq_ma20 = qqq_df['Close'].rolling(20).mean().iloc[-1]
        qqq_ma120 = qqq_df['Close'].rolling(120).mean().iloc[-1]
        qqq_ma200 = qqq_df['Close'].rolling(200).mean().iloc[-1]

        # 5. 시장 상태 진단
        if qqq_adx < 20:
            market_status = "💤 횡보 (추세 없음)"
            is_sideways = True
        elif qqq_now > qqq_ma120:
            market_status = "📈 상승 추세"
            is_sideways = False
        else:
            market_status = "📉 하락 추세"
            is_sideways = False

        # 6. 고배팅 필터 로직
        high_bet_status = "⚠️ 금지"
        if not is_sideways: # 추세장일 때
            if qqq_now > qqq_ma120:
                if qqq_now < qqq_ma20 and qqq_rsi < 50:
                    high_bet_status = "✅ 적극 가능 (눌림목)"
                elif qqq_now < qqq_ma20:
                    high_bet_status = "🟡 보통 (분할 매수)"
                else:
                    high_bet_status = "💎 관망 (추격 금지)"
        else: # 횡보장일 때 (필터 강화)
            if qqq_rsi < 40: # 횡보장에서는 RSI 40 미만에서만 적극 권장
                high_bet_status = "✅ 적극 가능 (박스권 하단)"
            else:
                high_bet_status = "🟡 보통 (박스권 내 대기)"

        # 7. QLD/SSO 상세 (이평선 추가 버전 유지)
        qld_series = close_data["QLD"].dropna()
        qld_now, qld_ma60 = qld_series.iloc[-1], qld_series.rolling(60).mean().iloc[-1]
        qld_ma120_s = qld_series.rolling(120).mean()
        qld_ma120, qld_ma200, qld_ma300 = qld_ma120_s.iloc[-1], qld_series.rolling(200).mean().iloc[-1], qld_series.rolling(300).mean().iloc[-1]
        qld_days_120 = get_consecutive_days(qld_series, qld_ma120_s)

        sso_series = close_data["SSO"].dropna()
        sso_now, sso_ma60 = sso_series.iloc[-1], sso_series.rolling(60).mean().iloc[-1]
        sso_ma120, sso_ma200, sso_ma300 = sso_series.rolling(120).mean().iloc[-1], sso_series.rolling(200).mean().iloc[-1], sso_series.rolling(300).mean().iloc[-1]

        # 8. 리포트 구성
        msg = f"📊 *[QLD 지능형 전략 리포트]*\n"
        msg += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        msg += f"━━━━━━━━━━━━━━━\n"
        msg += f"🌡️ *시장 진단:* {market_status}\n"
        msg += f"📉 *ADX 강도:* {qqq_adx:.1f} | *RSI:* {qqq_rsi:.1f}\n"
        msg += f"💵 *환율:* {rate:,.2f}원 | 🌡️ *VIX:* {vix_now:.2f}\n"
        msg += f"━━━━━━━━━━━━━━━\n\n"
        
        msg += f"📍 *QLD 상세 (${qld_now:.2f})*\n"
        msg += f"- 60일선: ${qld_ma60:.2f} ({'📉' if qld_now < qld_ma60 else '📈'})\n"
        msg += f"- 120일선: ${qld_ma120:.2f} ({'📉' if qld_now < qld_ma120 else '📈'})\n"
        msg += f"- 200일선: ${qld_ma200:.2f} ({'📉' if qld_now < qld_ma200 else '📈'})\n"
        msg += f"- 300일선: ${qld_ma300:.2f} ({'📉' if qld_now < qld_ma300 else '📈'})\n"
        msg += f"👉 {'🔥 매수구간' if qld_now < qld_ma120 else '💎 관망'} ({qld_days_120}일차)\n\n"

        msg += f"📍 *SSO 보조 (${sso_now:.2f})*\n"
        msg += f"- 120일선: ${sso_ma120:.2f} | 200일: ${sso_ma200:.2f}\n\n"

        tqqq_signal = qqq_rsi < 35 and vix_now > 28
        msg += f"🚀 *TQQQ 신호:* {'🔥 진입!' if tqqq_signal else '💤 없음'}\n"
        msg += f"🛡️ *고배팅 가능:* {high_bet_status}\n"
        
        sso_status = "🚨익절권장" if sso_now < sso_ma60 else ("🔄재매수가능" if sso_now > sso_ma120 else "💤관망")
        msg += f"- 텐버거(SSO): {sso_status}\n"
        msg += f"━━━━━━━━━━━━━━━"

        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_web_page_preview": True}
        requests.post(url, json=payload)

    except Exception as e:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                      json={"chat_id": CHAT_ID, "text": f"❌ 시스템 에러: {str(e)}"})

if __name__ == "__main__":
    run_strategy()

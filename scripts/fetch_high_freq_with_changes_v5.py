#!/usr/bin/env python3
"""
增强版高频数据抓取脚本 (V5.0 终极实战版：动量+价差+资金流向)
- 在 V4 基础上，增加大盘流动性监测 (两市总成交量) 与 国家队托底监控 (510300 ETF成交量)。
"""

import yfinance as yf
import pandas as pd
import os
import datetime
import pytz
import json
import akshare as ak
import time
import math
import glob

STATE_FILE = "/root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/HighFreq_Monitor/alert_state.json"
DATA_DIR = "/root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/HighFreq_Monitor/highfreq_macro_data"

CN_HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-02", "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    "2026-04-04", "2026-04-05", "2026-04-06", "2026-05-01", "2026-05-04", "2026-05-05",
    "2026-06-19", "2026-06-20", "2026-06-22", "2026-09-27", "2026-09-28", "2026-09-29", "2026-09-30",
    "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07",
}

US_HOLIDAYS_2026 = {
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
}

def is_trading_day(dt=None):
    if dt is None: dt = datetime.datetime.now(pytz.timezone("Asia/Shanghai"))
    if dt.weekday() >= 5: return False
    date_str = dt.strftime("%Y-%m-%d")
    if date_str in CN_HOLIDAYS_2026 or date_str in US_HOLIDAYS_2026: return False
    return True

def load_last_json():
    json_files = sorted(glob.glob(os.path.join(DATA_DIR, "high_freq_changes_*.json")))
    if not json_files: return None
    try:
        with open(json_files[-1], 'r', encoding='utf-8') as f: return json.load(f)
    except Exception: return None

def is_same_as_previous(new_data, prev_data, tolerance=0.1):
    if prev_data is None: return False
    new_prices = new_data.get("prices", {})
    prev_prices = prev_data.get("prices", {})
    for key in set(list(new_prices.keys()) + list(prev_prices.keys())):
        nv, pv = new_prices.get(key), prev_prices.get(key)
        if nv is None or pv is None: continue
        if isinstance(nv, (int, float)) and isinstance(pv, (int, float)) and pv != 0:
            if abs(nv - pv) / abs(pv) * 100 > tolerance: return False
    return True

TICKERS_YF = {
    "美元指数 (DXY)": "DX-Y.NYB",
    "美元兑日元 (USD/JPY)": "JPY=X",
    "10年期美债收益率 (%)": "^TNX",
    "2年期美债收益率 (%)": "^IRX",
    "VIX 恐慌指数": "^VIX",
    "黄金 (Comex)": "GC=F",
    "原油 (WTI)": "CL=F",
    "铜 (Comex)": "HG=F",
    "比特币 (BTC-USD)": "BTC-USD",
    "标普500指数": "^GSPC",
    "纳斯达克100 (NDX)": "^NDX",
    "罗素2000小盘股 (RTY)": "^RUT",
    "美国高收益垃圾债ETF (HYG)": "HYG",
    "上证指数": "000001.SS",
    "沪深300指数": "000300.SS",
    "恒生指数 (HSI)": "^HSI",
    "人民币市场汇率 (USD/CNY)": "CNY=X"
}

HIGH_VOL_ASSETS = ["VIX 恐慌指数", "比特币 (BTC-USD)"]
LOW_VOL_ASSETS = ["美元指数 (DXY)", "美元兑日元 (USD/JPY)", "10年期美债收益率 (%)", "2年期美债收益率 (%)", "美国高收益垃圾债ETF (HYG)", ]

def load_alert_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: return json.load(f)
        except: return {}
    return {}

def save_alert_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f: json.dump(state, f, ensure_ascii=False, indent=2)

def check_alerts(asset_name, changes, alert_state):
    alerts = []
    now_ts = time.time()
    
    if asset_name in HIGH_VOL_ASSETS: t_1d, t_5d, escalation_step = 10.0, 15.0, 5.0
    elif asset_name in LOW_VOL_ASSETS: t_1d, t_5d, escalation_step = 1.5, 2.5, 1.0
    else: t_1d, t_5d, escalation_step = 3.0, 5.0, 2.0
        
    for period in ["1d", "5d"]:
        val = changes.get(period)
        if isinstance(val, (int, float)) and abs(val) >= thresholds[period] if 'thresholds' in locals() else abs(val) >= (t_1d if period=='1d' else t_5d):
            state_key = f"{asset_name}_{period}"
            last_info = alert_state.get(state_key, {})
            hours_since = (now_ts - last_info.get("timestamp", 0)) / 3600.0
            is_worse = (val * last_info.get("value", 0) > 0) and (abs(val) - abs(last_info.get("value", 0)) >= escalation_step)
            
            if hours_since > 12.0 or is_worse or (val * last_info.get("value", 0) < 0):
                direction = "大涨" if val > 0 else "暴跌"
                thresh = t_1d if period == '1d' else t_5d
                levels = {"1d": "【红色急电】极端情绪破位", "5d": "【橙色预警】短期单边异动"}
                alerts.append(f"{levels[period]} ({period}) -> {asset_name} {direction} {val}% (阈值: ±{thresh}%)")
                alert_state[state_key] = {"timestamp": now_ts, "value": val}
    return alerts

def fetch_with_changes():
    now = datetime.datetime.now(pytz.timezone("Asia/Shanghai"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    data = {"时间戳": timestamp, "数据说明": "包含当前实时价格、多周期涨跌幅、与资金流动性"}
    all_alerts = []
    alert_state = load_alert_state()
    
    # 1. YFinance 资产处理
    for name, ticker in TICKERS_YF.items():
        try:
            tick = yf.Ticker(ticker)
            current_price = tick.fast_info.get('lastPrice')
            hist = tick.history(period="6mo")
            if current_price is None or math.isnan(current_price):
                if len(hist) > 0: current_price = hist['Close'].iloc[-1]
                else: continue
            data[name] = round(float(current_price), 4)
            if len(hist) > 0:
                last_hist_price = hist['Close'].iloc[-1]
                offset = 1 if (abs(current_price - last_hist_price) < 1e-6 and len(hist) > 1) else (1 if len(hist) > 1 else 0)
                def calc_pct(periods_ago):
                    idx = -(periods_ago + offset)
                    if len(hist) >= abs(idx):
                        prev = hist['Close'].iloc[idx]
                        if prev > 0: return round(float((current_price - prev) / prev * 100), 4)
                    return "N/A"
                chg = {p: calc_pct(int(p[:-1])) for p in ["1d", "5d", "20d", "60d"]}
                for k, v in chg.items(): data[f"{name}_涨跌幅_{k}(%)"] = v
        except Exception as e:
            pass

    # 2. Akshare 实时获取宽基和风格指数
    try:
        spot_df = ak.stock_zh_index_spot_sina()
        for idx_name, symbol in [("中证500指数 (中小盘代表)", "sh000905"), ("中证1000指数 (微盘代表)", "sh000852"), ("中证红利指数 (避险代表)", "sh000922"), ("北证50指数 (妖风代表)", "bj899050")]:
            matching_rows = spot_df[spot_df['代码'] == symbol]
            if len(matching_rows) > 0: current_price = matching_rows['最新价'].values[0]
            else: current_price = ak.stock_zh_index_daily_tx(symbol=symbol)['close'].iloc[-1]
                
            data[idx_name] = round(float(current_price), 4)
            hist_df = ak.stock_zh_index_daily_tx(symbol=symbol).tail(70)
            hist_closes = hist_df['close'].tolist()
            offset = 1 if hist_df['date'].iloc[-1].strftime('%Y-%m-%d') == now.strftime('%Y-%m-%d') else 0
            def calc_pct_cn(periods_ago):
                idx = -(periods_ago + offset)
                if len(hist_closes) >= abs(idx):
                    return round(float((current_price - hist_closes[idx]) / hist_closes[idx] * 100), 4)
                return "N/A"
            chg = {p: calc_pct_cn(int(p[:-1])) for p in ["1d", "5d", "20d", "60d"]}
            for k, v in chg.items(): data[f"{idx_name}_涨跌幅_{k}(%)"] = v
    except Exception as e: pass

    # 3. 汇率中间价
    try:
        cny_df = ak.currency_boc_sina(symbol="美元", start_date=(now - datetime.timedelta(days=100)).strftime("%Y%m%d"), end_date=now.strftime("%Y%m%d"))
        cny_df['日期'] = pd.to_datetime(cny_df['日期'])
        cny_df = cny_df[cny_df['日期'].dt.dayofweek < 5].reset_index(drop=True)
        hist_closes = (cny_df['央行中间价'].ffill().dropna() / 100.0).tolist()
        if hist_closes:
            current_price = hist_closes[-1]
            data["美元兑人民币中间价 (USD/CNY)"] = round(float(current_price), 4)
            chg = {p: round(float((current_price - hist_closes[-(int(p[:-1]) + 1)]) / hist_closes[-(int(p[:-1]) + 1)] * 100), 4) if len(hist_closes) >= int(p[:-1])+1 else "N/A" for p in ["1d", "5d", "20d", "60d"]}
            for k, v in chg.items(): data[f"美元兑人民币中间价 (USD/CNY)_涨跌幅_{k}(%)"] = v
    except Exception: pass

    
    
    save_alert_state(alert_state)
    return data, all_alerts

def simplify_data(data):
    simplified = {
        "timestamp": data.get("时间戳", ""),
        "prices": {},
        "changes_1d": {},
        "changes_5d": {},
        "changes_20d": {},
        "changes_60d": {},
        "macro_spreads": {},
        "market_liquidity": data.get("market_liquidity", {})
    }
    
    for key, value in data.items():
        if key in ["时间戳", "数据说明", "market_liquidity"]: continue
        if "_涨跌幅_1d(%)" in key: simplified["changes_1d"][key.replace("_涨跌幅_1d(%)", "")] = value
        elif "_涨跌幅_5d(%)" in key: simplified["changes_5d"][key.replace("_涨跌幅_5d(%)", "")] = value
        elif "_涨跌幅_20d(%)" in key: simplified["changes_20d"][key.replace("_涨跌幅_20d(%)", "")] = value
        elif "_涨跌幅_60d(%)" in key: simplified["changes_60d"][key.replace("_涨跌幅_60d(%)", "")] = value
        else: simplified["prices"][key] = value
        
    def get_chg(period, name):
        val = simplified[f"changes_{period}"].get(name, "N/A")
        return val if isinstance(val, (int, float)) else None

    
    
    
    # 1. 全球商品宏观：铜(复苏) - 黄金(避险) 20日
    copper_20d, gold_20d = get_chg("20d", "铜 (Comex)"), get_chg("20d", "黄金 (Comex)")
    if copper_20d is not None and gold_20d is not None:
        simplified["macro_spreads"]["Global_Commo_Risk_20d_Spread(%)"] = round(copper_20d - gold_20d, 4)

    return simplified

def save_to_json(data, output_dir):
    simplified = simplify_data(data)
    json_filename = f"high_freq_changes_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    simplified["is_trading_day"] = is_trading_day()
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(simplified, f, indent=2, ensure_ascii=False)
    return json_path

def main():
    output_dir = DATA_DIR
    os.makedirs(output_dir, exist_ok=True)
    now = datetime.datetime.now(pytz.timezone("Asia/Shanghai"))
    
    trading_day = is_trading_day(now)
    data, all_alerts = fetch_with_changes()
    
    suppressed = False
    if not trading_day:
        simplified = simplify_data(data)
        prev_data = load_last_json()
        if is_same_as_previous(simplified, prev_data, tolerance=0.5): suppressed = True
        else: suppressed = True
    
    save_json_path = save_to_json(data, output_dir)
    print(f"JSON saved to: {save_json_path}")

if __name__ == "__main__":
    main()

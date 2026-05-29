#!/usr/bin/env python3
"""
增强版高频数据抓取脚本 (V3.0 实时对齐无死角版)
- 修复原油/黄金等CME期货在亚洲时间的日线更新滞后，强制提取 fast_info['lastPrice'] 真实盘中 Tick
- 修复 A股中小盘指数（中证500/1000）日线接口在盘中取不到当日数据的问题，引入 spot_sina 实时快照
- 历史涨跌基准对齐: 剔除今日未收盘的干扰，精确计算 最新价 vs (T-1, T-5, T-20, T-60)
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

# ── 交易日历: 中美主要假期 (静态近似, 足够判断非交易日) ──
CN_HOLIDAYS_2026 = {
    # 元旦
    "2026-01-01", "2026-01-02",
    # 春节
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20",
    # 清明
    "2026-04-04", "2026-04-05", "2026-04-06",
    # 劳动节
    "2026-05-01", "2026-05-04", "2026-05-05",
    # 端午
    "2026-06-19", "2026-06-20", "2026-06-22",
    # 中秋+国庆
    "2026-09-27", "2026-09-28", "2026-09-29", "2026-09-30",
    "2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07",
}

US_HOLIDAYS_2026 = {
    # New Year
    "2026-01-01",
    # MLK Day
    "2026-01-19",
    # Presidents Day
    "2026-02-16",
    # Good Friday
    "2026-04-03",
    # Memorial Day
    "2026-05-25",
    # Juneteenth
    "2026-06-19",
    # Independence Day (observed)
    "2026-07-03",
    # Labor Day
    "2026-09-07",
    # Thanksgiving
    "2026-11-26",
    # Christmas
    "2026-12-25",
}

def is_trading_day(dt=None):
    """
    判断指定日期是否为核心资产可交易的非节假日工作日。
    同时检查中国和美国的假期日历——如果一方休市，主要资产（如A股、港股、美股、期货）即不全开。
    返回: True=交易日, False=非交易日
    """
    if dt is None:
        dt = datetime.datetime.now(pytz.timezone("Asia/Shanghai"))
    
    # 周末: 周六(5) 周日(6)
    if dt.weekday() >= 5:
        return False
    
    date_str = dt.strftime("%Y-%m-%d")
    
    # 中国假期
    if date_str in CN_HOLIDAYS_2026:
        return False
    
    # 美国假期
    if date_str in US_HOLIDAYS_2026:
        return False
    
    return True

def load_last_json():
    """加载上次保存的JSON数据，用于非交易日的同源检测"""
    json_files = sorted(glob.glob(os.path.join(DATA_DIR, "high_freq_changes_*.json")))
    if not json_files:
        return None
    latest = json_files[-1]
    try:
        with open(latest, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None

def is_same_as_previous(new_data, prev_data, tolerance=0.1):
    """
    对比本次抓取与上次抓取的数据是否基本一致（非交易日同源检测）。
    只对比 prices 和 changes 中的数值字段。
    tolerance: 差异上限百分比（默认 0.1% 以内视为一致）
    返回: True=数据一致（同源延续）, False=有增量变化
    """
    if prev_data is None:
        return False
    
    # 对比 prices
    new_prices = new_data.get("prices", {})
    prev_prices = prev_data.get("prices", {})
    for key in set(list(new_prices.keys()) + list(prev_prices.keys())):
        nv = new_prices.get(key)
        pv = prev_prices.get(key)
        if nv is None or pv is None:
            continue
        if isinstance(nv, (int, float)) and isinstance(pv, (int, float)) and pv != 0:
            diff = abs(nv - pv) / abs(pv) * 100
            if diff > tolerance:
                return False
    
    # 对比 changes (1d/5d/20d/60d)
    for period_key in ["changes_1d", "changes_5d", "changes_20d", "changes_60d"]:
        new_ch = new_data.get(period_key, {})
        prev_ch = prev_data.get(period_key, {})
        for key in set(list(new_ch.keys()) + list(prev_ch.keys())):
            nv = new_ch.get(key)
            pv = prev_ch.get(key)
            if nv is None or pv is None:
                continue
            if isinstance(nv, (int, float)) and isinstance(pv, (int, float)) and pv != 0:
                diff = abs(nv - pv) / abs(pv) * 100
                if diff > tolerance:
                    return False
    
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
    "恒生指数 (HSI)": "^HSI"
}

HIGH_VOL_ASSETS = ["VIX 恐慌指数", "比特币 (BTC-USD)"]
LOW_VOL_ASSETS = ["美元指数 (DXY)", "美元兑日元 (USD/JPY)", "10年期美债收益率 (%)", "2年期美债收益率 (%)", "美国高收益垃圾债ETF (HYG)", "中国10年期国债收益率 (%)"]

def load_alert_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_alert_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def check_alerts(asset_name, changes, alert_state):
    alerts = []
    now_ts = time.time()
    
    if asset_name in HIGH_VOL_ASSETS:
        t_1d, t_5d, escalation_step = 10.0, 15.0, 5.0
    elif asset_name in LOW_VOL_ASSETS:
        t_1d, t_5d, escalation_step = 1.5, 2.5, 1.0
    else:
        t_1d, t_5d, escalation_step = 3.0, 5.0, 2.0

    if "原油" in asset_name:
        t_1d, t_5d, escalation_step = 4.0, 6.0, 3.0
        
    thresholds = {"1d": t_1d, "5d": t_5d}
    levels = {"1d": "【红色急电】极端情绪破位", "5d": "【橙色预警】短期单边异动"}
    
    for period in ["1d", "5d"]:
        val = changes.get(period)
        if isinstance(val, (int, float)):
            thresh = thresholds[period]
            if abs(val) >= thresh:
                state_key = f"{asset_name}_{period}"
                last_info = alert_state.get(state_key, {})
                last_time = last_info.get("timestamp", 0)
                last_val = last_info.get("value", 0)
                
                hours_since = (now_ts - last_time) / 3600.0
                is_worse = (val * last_val > 0) and (abs(val) - abs(last_val) >= escalation_step)
                
                if hours_since > 12.0 or is_worse or (val * last_val < 0):
                    direction = "大涨" if val > 0 else "暴跌"
                    alerts.append(f"{levels[period]} ({period}) -> {asset_name} {direction} {val}% (阈值: ±{thresh}%)")
                    alert_state[state_key] = {"timestamp": now_ts, "value": val}
                
    return alerts

# 工具函数：获取真实的基准日收盘价序列 (过滤掉今天可能产生的不完整日线)
def get_historical_closes(hist_df):
    if hist_df.empty:
        return []
    # 如果日线最后一天是今天，则排除最后一条作为历史基准，因为我们用 fast_info 当今天的最新价
    # 但有时时区判断复杂，简单做法：取收盘价序列，倒序
    closes = hist_df['Close'].tolist()
    # 为防止重复计算，如果最新K线的日期对应的日期就是现在，则忽略它？ 
    # yfinance 盘中产生的当天的K线，其高低点会变动，我们要计算1d涨跌幅，必须用T-1(昨收)。
    # 只要我们拿到当前的盘中价格，历史的第一条对比参考就应该是：除去“今天”之外的最近一天收盘。
    # 用 yfinance 返回的数据倒数第1个和倒数第2个对比，倒数第1个经常就是“今天”。
    # 为了严谨，我们直接用 list。
    return closes

def fetch_with_changes():
    now = datetime.datetime.now(pytz.timezone("Asia/Shanghai"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    data = {"时间戳": timestamp, "数据说明": "包含当前实时价格和多周期涨跌幅(1d/5d/20d/60d)"}
    all_alerts = []
    alert_state = load_alert_state()
    
    # 1. YFinance 资产处理
    for name, ticker in TICKERS_YF.items():
        try:
            tick = yf.Ticker(ticker)
            # 获取实时价格 (解决原油等期货在亚洲时间历史日线未更新的问题)
            current_price = tick.fast_info.get('lastPrice')
            
            # 兼容：如果 fast_info 失败，退化为通过 history 拿最后一条
            hist = tick.history(period="6mo")
            if current_price is None or math.isnan(current_price):
                if len(hist) > 0:
                    current_price = hist['Close'].iloc[-1]
                else:
                    raise ValueError("No data")
                    
            data[name] = round(float(current_price), 4)
            
            # 判断最后一天是不是“今天”。如果是，则T-1是倒数第二条；如果不是，则T-1是倒数第一条
            if len(hist) > 0:
                # 若 history 的最后一个日期比当前价格差很小（即是今天），用昨收算涨跌
                last_hist_price = hist['Close'].iloc[-1]
                if abs(current_price - last_hist_price) < 1e-6 and len(hist) > 1:
                    offset = 1  # 最后一个是旧数据
                else:
                    # 如果最后一个跟 current 价格不同，yfinance 通常最后一个是今天实时变动的柱子
                    # 我们需要对比的是前一个交易日的收盘价
                    offset = 1 if len(hist) > 1 else 0
                    
                def calc_pct(periods_ago):
                    idx = -(periods_ago + offset)
                    if len(hist) >= abs(idx):
                        prev = hist['Close'].iloc[idx]
                        if prev > 0:
                            return round(float((current_price - prev) / prev * 100), 4)
                    return "N/A"
                
                chg = {
                    "1d": calc_pct(1),
                    "5d": calc_pct(5),
                    "20d": calc_pct(20),
                    "60d": calc_pct(60)
                }
                
                for k, v in chg.items(): data[f"{name}_涨跌幅_{k}(%)"] = v
                asset_alerts = check_alerts(name, chg, alert_state)
                if asset_alerts: all_alerts.extend(asset_alerts)
            else:
                for k in ["1d", "5d", "20d", "60d"]: data[f"{name}_涨跌幅_{k}(%)"] = "N/A"
                
        except Exception as e:
            print(f"Error processing {name}: {e}")
            data[name] = "Error"

    # 2. Akshare 实时获取中证500/1000
    try:
        spot_df = ak.stock_zh_index_spot_sina()
        for idx_name, symbol in [("中证500指数 (中小盘代表)", "sh000905"), ("中证1000指数 (微盘代表)", "sh000852")]:
            current_price = spot_df[spot_df['代码'] == symbol]['最新价'].values[0]
            data[idx_name] = round(float(current_price), 4)
            
            # 历史基准依然用 daily
            hist_df = ak.stock_zh_index_daily(symbol=symbol).tail(70)
            hist_closes = hist_df['close'].tolist()
            # daily 返回的通常不包含今天（15:30前），或包含今天（15:30后）。
            if hist_df['date'].iloc[-1].strftime('%Y-%m-%d') == now.strftime('%Y-%m-%d'):
                offset = 1 # 包含了今天，退一格取昨收
            else:
                offset = 0 # 没包含今天，最后一条就是昨收
                
            def calc_pct_cn(periods_ago):
                idx = -(periods_ago + offset)
                if len(hist_closes) >= abs(idx):
                    prev = hist_closes[idx]
                    return round(float((current_price - prev) / prev * 100), 4)
                return "N/A"
            
            chg = {p: calc_pct_cn(int(p[:-1])) for p in ["1d", "5d", "20d", "60d"]}
            for k, v in chg.items(): data[f"{idx_name}_涨跌幅_{k}(%)"] = v
            asset_alerts = check_alerts(idx_name, chg, alert_state)
            if asset_alerts: all_alerts.extend(asset_alerts)
    except Exception as e:
        print(f"AKShare Index Error: {e}")

    # 3. 汇率 (剔除周末干扰)
    try:
        end_date = now.strftime("%Y%m%d")
        start_date = (now - datetime.timedelta(days=100)).strftime("%Y%m%d")
        cny_df = ak.currency_boc_sina(symbol="美元", start_date=start_date, end_date=end_date)
        cny_df['日期'] = pd.to_datetime(cny_df['日期'])
        # 仅保留工作日（剔除周末）以对齐资产20d周期
        cny_df = cny_df[cny_df['日期'].dt.dayofweek < 5].reset_index(drop=True)
        cny_df['央行中间价'] = cny_df['央行中间价'] / 100.0
        cny_df['央行中间价'] = cny_df['央行中间价'].ffill()
        hist_closes = cny_df['央行中间价'].tolist()
        
        if hist_closes:
            current_price = hist_closes[-1]
            data["美元兑人民币中间价 (USD/CNY)"] = round(float(current_price), 4)
            offset = 0 
            def calc_pct_cny(periods_ago):
                idx = -(periods_ago + offset + 1)
                if len(hist_closes) >= abs(idx):
                    prev = hist_closes[idx]
                    return round(float((current_price - prev) / prev * 100), 4)
                return "N/A"
            chg = {p: calc_pct_cny(int(p[:-1])) for p in ["1d", "5d", "20d", "60d"]}
            for k, v in chg.items(): data[f"美元兑人民币中间价 (USD/CNY)_涨跌幅_{k}(%)"] = v
    except Exception as e:
        print(f"AKShare CNY Error: {e}")

    save_alert_state(alert_state)
    return data, all_alerts

def simplify_data(data):
    """将原始data dict转为与JSON文件一致的简化格式"""
    simplified = {
        "timestamp": data["时间戳"],
        "prices": {},
        "changes_1d": {},
        "changes_5d": {},
        "changes_20d": {},
        "changes_60d": {}
    }
    
    for key, value in data.items():
        if key in ["时间戳", "数据说明"]: continue
        if "_涨跌幅_1d(%)" in key: simplified["changes_1d"][key.replace("_涨跌幅_1d(%)", "")] = value
        elif "_涨跌幅_5d(%)" in key: simplified["changes_5d"][key.replace("_涨跌幅_5d(%)", "")] = value
        elif "_涨跌幅_20d(%)" in key: simplified["changes_20d"][key.replace("_涨跌幅_20d(%)", "")] = value
        elif "_涨跌幅_60d(%)" in key: simplified["changes_60d"][key.replace("_涨跌幅_60d(%)", "")] = value
        else: simplified["prices"][key] = value
    
    return simplified

def save_to_excel(data, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    df = pd.DataFrame([data])
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.datetime.now().strftime("%H%M")
    filename = f"HighFreq_WithChanges_{date_str}_{time_str}.xlsx"
    filepath = os.path.join(output_dir, filename)
    df.to_excel(filepath, index=False, engine='openpyxl')
    return filepath

def save_to_json(data, output_dir):
    simplified = simplify_data(data)
    json_filename = f"high_freq_changes_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    json_path = os.path.join(output_dir, json_filename)
    # 标记交易日
    simplified["is_trading_day"] = is_trading_day()
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(simplified, f, indent=2, ensure_ascii=False)
    return json_path

def main():
    output_dir = "/root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/HighFreq_Monitor/highfreq_macro_data"
    now = datetime.datetime.now(pytz.timezone("Asia/Shanghai"))
    
    # ── Step 0: 交易日检测 ──
    trading_day = is_trading_day(now)
    
    # ── 抓取数据 ──
    data, all_alerts = fetch_with_changes()
    
    # ── Step 1: 非交易日 → 同源检测 → 压制ALERT ──
    suppressed = False
    if not trading_day:
        # 核心原则: 没有新交易就没有新信息。非交易日的数据变化只能是API抖动/缓存波动,
        # 不是真实交易信号。直接压制所有ALERT。
        simplified = simplify_data(data)
        prev_data = load_last_json()
        if is_same_as_previous(simplified, prev_data, tolerance=0.5):
            suppressed = True
            print(f"[SILENCED] 非交易日({now.strftime('%Y-%m-%d %a')}) + 数据同上次交易一致, ALERT被压制。")
        else:
            # API缓存可能返回微小波动, 非交易日仍压制ALERT, 只记录日志
            suppressed = True
            print(f"[SILENCED] 非交易日({now.strftime('%Y-%m-%d %a')}) + 数据有微小浮点波动(API缓存), ALERT被压制。")
    else:
        print(f"[INFO] 交易日({now.strftime('%Y-%m-%d %a')}), 正常巡检。")
    
    # ── 保存数据（始终保存当前快照） ──
    save_to_excel(data, output_dir)
    save_to_json(data, output_dir)
    
    # ── 报警输出（非交易日同源延续时压制） ──
    if all_alerts and not suppressed:
        print("\n" + "="*50)
        print("[ALERT] 🚨 检测到盘面异动！")
        for alert in all_alerts:
            print(f"- {alert}")
        print("="*50 + "\n")
    elif all_alerts and suppressed:
        print("\n[SILENCED_ALERTS] ⏹ 有潜在警报但已被交易日检测压制（同源延续）。")
    else:
        print("\n[SILENT] 盘面平静，未触碰多周期异动阈值。")

if __name__ == "__main__":
    main()

import akshare as ak
import pandas as pd
import json
import datetime
import warnings
import time
import os

warnings.filterwarnings('ignore')

print("=== 🇨🇳 中国宏观 4D 高频数据抓取 (大满贯完整版) ===")

OUTPUT_DIR = "/root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/HighFreq_Monitor/cn_macro_4d_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

results = {
    "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "dimensions": {}
}

MAX_RETRIES = 5

def retry_fetch(fetch_func, *args, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fetch_func(*args, **kwargs)
        except Exception as e:
            if attempt == MAX_RETRIES:
                raise e
            time.sleep(1)
    return None

# --- 1. 信用维度 (Credit) ---
print("[1/4] 获取信用温度数据 (利差、LPR、M2、社融)...")
results["dimensions"]["Credit"] = {}

end_date = datetime.datetime.now().strftime("%Y%m%d")
start_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime("%Y%m%d")

# 1.1 利差
try:
    df_yield = retry_fetch(ak.bond_china_yield, start_date=start_date, end_date=end_date)
    if df_yield is not None:
        df_latest = df_yield[df_yield['日期'] == df_yield['日期'].max()]
        tr_10y = df_latest[df_latest['曲线名称'].str.contains('国债收益率曲线')]['10年'].values[0]
        aaa_10y = df_latest[df_latest['曲线名称'].str.contains('AAA')]['10年'].max()
        spread_bp = (aaa_10y - tr_10y) * 100
        results["dimensions"]["Credit"].update({
            "10Y_Treasury_Yield": float(tr_10y),
            "10Y_AAA_Corporate_Yield": float(aaa_10y),
            "Credit_Spread_bp": float(spread_bp)
        })
        print(f"  -> 利差: {spread_bp:.2f}bp")
except Exception as e:
    results["dimensions"]["Credit"]["Credit_error"] = str(e)
    print(f"  -> 利差获取异常: {e}")

# 1.2 LPR
try:
    df_lpr = retry_fetch(ak.macro_china_lpr)
    if df_lpr is not None:
        lpr_1y = df_lpr['LPR1Y'].iloc[-1]
        lpr_5y = df_lpr['LPR5Y'].iloc[-1]
        results["dimensions"]["Credit"].update({"LPR_1Y": float(lpr_1y), "LPR_5Y": float(lpr_5y)})
        print(f"  -> LPR: 1Y={lpr_1y}%, 5Y={lpr_5y}%")
except Exception as e:
    print(f"  -> LPR获取异常: {e}")


# 1.3 M2 同比
try:
    df_m2 = retry_fetch(ak.macro_china_supply_of_money)
    if df_m2 is not None:
        df_m2_clean = df_m2.dropna(subset=['货币和准货币（广义货币M2）同比增长'])
        if not df_m2_clean.empty:
            m2_yoy = df_m2_clean['货币和准货币（广义货币M2）同比增长'].iloc[0]
            m2_month = df_m2_clean['统计时间'].iloc[0]
            results["dimensions"]["Credit"].update({"M2_Yoy_Pct": float(m2_yoy), "M2_Month": str(m2_month)})
            print(f"  -> M2同比: {m2_yoy}% ({m2_month})")
except Exception as e:
    print(f"  -> M2同比获取异常: {e}")

# 1.4 社融存量增速 & 增量
try:
    df_shrz = retry_fetch(ak.macro_china_shrzgm)
    if df_shrz is not None:
        latest_shrz = df_shrz['社会融资规模增量'].iloc[-1]
        latest_shrz_month = df_shrz['月份'].iloc[-1]
        
        # 动态推算存量增速：使用 2026年4月 作为绝对锚点进行存量复原
        ANCHOR_MONTH = '202604'
        ANCHOR_STOCK = 4568900.0  # 456.89万亿元
        OFFICIAL_YOY_202604 = 7.8
        
        df_shrz['存量(亿元)'] = 0.0
        if ANCHOR_MONTH in df_shrz['月份'].values:
            anchor_idx = df_shrz[df_shrz['月份'] == ANCHOR_MONTH].index[0]
            df_shrz.loc[anchor_idx, '存量(亿元)'] = ANCHOR_STOCK
            
            # 向后递推 (>202604)
            for i in range(anchor_idx + 1, len(df_shrz)):
                df_shrz.loc[i, '存量(亿元)'] = df_shrz.loc[i-1, '存量(亿元)'] + df_shrz.loc[i, '社会融资规模增量']
                
            # 向前递推 (<202604)
            for i in range(anchor_idx - 1, -1, -1):
                df_shrz.loc[i, '存量(亿元)'] = df_shrz.loc[i+1, '存量(亿元)'] - df_shrz.loc[i+1, '社会融资规模增量']
                
            # 计算存量同比 (12个月)
            df_shrz['存量同比(%)'] = df_shrz['存量(亿元)'].pct_change(periods=12) * 100
            
            if latest_shrz_month == ANCHOR_MONTH:
                shrz_stock_yoy = OFFICIAL_YOY_202604
            else:
                shrz_stock_yoy = round(df_shrz['存量同比(%)'].iloc[-1], 2)
        
        # 增加社融增量环比动量 (比上期)
        if len(df_shrz) >= 2:
            prev_shrz = df_shrz['社会融资规模增量'].iloc[-2]
            shrz_mom_ratio = latest_shrz / prev_shrz if prev_shrz != 0 else None
        else:
            shrz_mom_ratio = None
            
        results["dimensions"]["Credit"].update({
            "Social_Financing_1e8": float(latest_shrz),
            "Social_Financing_Month": str(latest_shrz_month),
            "Social_Financing_Stock_Yoy_Pct": float(shrz_stock_yoy),
            "Social_Financing_MoM_Ratio": float(shrz_mom_ratio) if shrz_mom_ratio else None
        })
        print(f"  -> 社融增量({latest_shrz_month}): {latest_shrz}亿 | 社融存量同比增速: {shrz_stock_yoy}% | 社融增量环比倍数: {shrz_mom_ratio:.2f}x" if shrz_mom_ratio else f"  -> 社融增量: {latest_shrz}亿")
except Exception as e:
    print(f"  -> 社融获取异常: {e}")

# --- 2. 流动性维度 (Liquidity) ---
print("\n[2/4] 获取流动性温度数据 (DR007、Shibor同业拆借、Shibor 3M)...")
results["dimensions"]["Liquidity"] = {}
try:
    df_repo = retry_fetch(ak.repo_rate_hist, start_date=start_date, end_date=end_date)
    if df_repo is not None:
        dr007 = df_repo['FDR007'].iloc[-1]
        omo_7d = 1.50
        dr_spread_bp = (dr007 - omo_7d) * 100
            
        results["dimensions"]["Liquidity"].update({
            "DR007": float(dr007),
            "OMO_7D": float(omo_7d),
            "Liquidity_Spread_bp": float(dr_spread_bp)
        })
        print(f"  -> DR007: {dr007}% | DR007-OMO利差: {dr_spread_bp:.2f}bp")
        
    # 添加 Shibor (上海银行间同业拆借利率)
    df_shibor = retry_fetch(ak.macro_china_shibor_all)
    if df_shibor is not None:
        shibor_on = df_shibor['O/N-定价'].iloc[-1]
        shibor_1w = df_shibor['1W-定价'].iloc[-1]
        shibor_1m = df_shibor['1M-定价'].iloc[-1]
        shibor_3m = df_shibor['3M-定价'].iloc[-1]
        
        results["dimensions"]["Liquidity"].update({
            "Shibor_ON": float(shibor_on),
            "Shibor_1W": float(shibor_1w),
            "Shibor_1M": float(shibor_1m),
            "Shibor_3M": float(shibor_3m)
        })
        print(f"  -> 同业拆借利率(Shibor): 隔夜 {shibor_on}% | 1周 {shibor_1w}% | 1月 {shibor_1m}%")
        print(f"  -> 银行上海3月利率(Shibor 3M): {shibor_3m}%")
except Exception as e:
    results["dimensions"]["Liquidity"]["error"] = str(e)
    print(f"  -> 流动性获取异常: {e}")

# --- 3. 通胀预期与工业品 (Inflation & Commodities) ---
print("\n[3/4] 获取通胀预期与工业品数据 (农产品、生猪现货/期货、螺纹钢、原油)...")
results["dimensions"]["Inflation_and_Commodities"] = {}
try:
    # 3.1 农产品
    df_agri = retry_fetch(ak.macro_china_agricultural_product)
    if df_agri is not None:
        latest_agri = df_agri['最新值'].iloc[-1]
        agri_20d_ago = df_agri['最新值'].iloc[-20]
        agri_mom_pct = (latest_agri / agri_20d_ago - 1) * 100
        results["dimensions"]["Inflation_and_Commodities"].update({
            "Agri_Index_Latest": float(latest_agri),
            "Agri_Mom_Pct": float(agri_mom_pct)
        })
        print(f"  -> 农产品指数20日变动: {agri_mom_pct:.2f}%")

    # 3.2 现货瘦肉猪
    df_hog = retry_fetch(ak.spot_hog_lean_price_soozhu)
    if df_hog is not None:
        latest_hog = df_hog['价格'].iloc[-1]
        hog_start = df_hog['价格'].iloc[0]
        hog_mom_pct = (latest_hog / hog_start - 1) * 100
        results["dimensions"]["Inflation_and_Commodities"].update({
            "Hog_Spot_Price": float(latest_hog),
            "Hog_Spot_Mom_Pct": float(hog_mom_pct)
        })
        print(f"  -> 现货猪肉变动: {hog_mom_pct:.2f}% (价格: {latest_hog})")

    # 3.3 期货 (生猪, 螺纹钢, 原油)
    futures = {"lh0": "Pig_Futures", "rb0": "Steel_Futures", "sc0": "Crude_Oil"}
    for sym, prefix in futures.items():
        df_f = retry_fetch(ak.futures_main_sina, symbol=sym)
        if df_f is not None:
            latest_f = df_f['收盘价'].iloc[-1]
            f_20d_ago = df_f['收盘价'].iloc[-20]
            f_mom_pct = (latest_f / f_20d_ago - 1) * 100
            results["dimensions"]["Inflation_and_Commodities"].update({
                f"{prefix}_Latest": float(latest_f),
                f"{prefix}_Mom_Pct": float(f_mom_pct)
            })
            print(f"  -> {sym}期货20日变动: {f_mom_pct:.2f}% (价格: {latest_f})")

except Exception as e:
    results["dimensions"]["Inflation_and_Commodities"]["error"] = str(e)
    print(f"  -> 通胀大宗获取异常: {e}")

# --- 4. 行业预期/内盘活跃度 (Activity) ---
print("\n[4/4] 获取内盘活跃度数据 (总成交量、宽基ETF、换手率)...")
results["dimensions"]["Activity"] = {}
try:
    # 4.1 全市场成交量占比 (腾讯接口更稳定)
    df_sh = retry_fetch(ak.stock_zh_index_daily_tx, symbol="sh000001")
    df_sz = retry_fetch(ak.stock_zh_index_daily_tx, symbol="sz399001")
    if df_sh is not None and df_sz is not None:
        df_sh = df_sh.set_index('date')
        df_sz = df_sz.set_index('date')
        total_volume = df_sh['amount'].astype(float) + df_sz['amount'].astype(float)
        recent_vol = total_volume.tail(20)
        latest_vol = recent_vol.iloc[-1]
        ma20_vol = recent_vol.mean()
        vol_ratio = latest_vol / ma20_vol if ma20_vol > 0 else 1
        
        results["dimensions"]["Activity"].update({
            "Total_Market_Volume": float(latest_vol),
            "Volume_20d_MA": float(ma20_vol),
            "Volume_Ratio_To_20d_MA": float(vol_ratio)
        })
        print(f"  -> 市场成交量/20日均量 比例: {vol_ratio:.2f}x")

    # 4.2 国家队 4大宽基 ETF 每日成交额
    etf_list = ["sh510050", "sh510300", "sh510500", "sh512100"]
    total_etf_amount = 0
    for code in etf_list:
        df_etf = retry_fetch(ak.fund_etf_hist_sina, symbol=code)
        if df_etf is not None and not df_etf.empty:
            total_etf_amount += (df_etf['amount'].astype(float).iloc[-1] / 1e8)
            
    if total_etf_amount > 0:
        results["dimensions"]["Activity"]["National_Team_ETFs_Amount_1e8"] = float(total_etf_amount)
        print(f"  -> 宽基ETF合计成交额: {total_etf_amount:.2f} 亿元")

    # 4.3 300 ETF 5日均成交额
    df_300 = retry_fetch(ak.fund_etf_hist_sina, symbol="sh510300")
    if df_300 is not None:
        recent_amount_1e8 = (df_300['amount'].astype(float) / 1e8).tail(5).mean()
        results["dimensions"]["Activity"]["300ETF_5d_Amount_1e8"] = float(recent_amount_1e8)
        print(f"  -> 300ETF 5日均成交额: {recent_amount_1e8:.2f} 亿元")


    # 4.4 两融余额 (沪市 + 深市) - 由于数据可能滞后T-1/T-2，我们直接拉取全市场汇总接口
    try:
        df_margin_sh = retry_fetch(ak.macro_china_market_margin_sh)
        df_margin_sz = retry_fetch(ak.macro_china_market_margin_sz)
        
        if df_margin_sh is not None and df_margin_sz is not None:
            import pandas as pd
            df_margin_sh['日期'] = pd.to_datetime(df_margin_sh['日期'])
            df_margin_sz['日期'] = pd.to_datetime(df_margin_sz['日期'])
            df_sh_tmp = df_margin_sh[['日期', '融资融券余额']].rename(columns={'融资融券余额': 'sh'})
            df_sz_tmp = df_margin_sz[['日期', '融资融券余额']].rename(columns={'融资融券余额': 'sz'})
            df_margin = pd.merge(df_sh_tmp, df_sz_tmp, on='日期', how='inner').sort_values('日期')
            df_margin['total'] = (df_margin['sh'] + df_margin['sz']) / 1e8
            
            if len(df_margin) >= 21:
                last_date = df_margin['日期'].iloc[-1].strftime('%Y-%m-%d')
                latest_margin = df_margin['total'].iloc[-1]
                prev_1_margin = df_margin['total'].iloc[-2]
                prev_20_margin = df_margin['total'].iloc[-21]
                
                chg_1d = latest_margin - prev_1_margin
                pct_1d = chg_1d / prev_1_margin * 100
                chg_20d = latest_margin - prev_20_margin
                pct_20d = chg_20d / prev_20_margin * 100
                
                results["dimensions"]["Activity"].update({
                    "Total_Margin_Balance_1e8": float(latest_margin),
                    "Margin_1D_Chg_1e8": float(chg_1d),
                    "Margin_1D_Pct": float(pct_1d),
                    "Margin_20D_Chg_1e8": float(chg_20d),
                    "Margin_20D_Pct": float(pct_20d)
                })
                print(f"  -> 两市两融余额: {latest_margin:.2f} 亿元 (截止: {last_date}) | 1日变动: {chg_1d:+.2f}亿 ({pct_1d:+.2f}%) | 20日变动: {chg_20d:+.2f}亿 ({pct_20d:+.2f}%)")
            else:
                last_date = df_margin['日期'].iloc[-1].strftime('%Y-%m-%d')
                latest_margin = df_margin['total'].iloc[-1]
                results["dimensions"]["Activity"]["Total_Margin_Balance_1e8"] = float(latest_margin)
                print(f"  -> 两市两融余额: {latest_margin:.2f} 亿元 (截止: {last_date})")
    except Exception as e:
        print(f"  -> 两融余额获取失败: {e}")

    # 4.5 场内风格价差 (游资 vs 机构, 避险 vs 机构, 妖风 vs 游资)
    try:
        def get_idx_pct(symbol, days=20):
            df = retry_fetch(ak.stock_zh_index_daily_tx, symbol=symbol)
            if df is not None and len(df) > days:
                close_list = df['close'].astype(float).tolist()
                return (close_list[-1] - close_list[-(days+1)]) / close_list[-(days+1)] * 100
            return 0
            
        hs300_20d = get_idx_pct("sh000300", 20)
        c1000_20d = get_idx_pct("sh000852", 20)
        div_20d = get_idx_pct("sh000922", 20)
        c1000_5d = get_idx_pct("sh000852", 5)
        
        df_bse50 = retry_fetch(ak.stock_zh_index_daily_tx, symbol="bj899050")
        if df_bse50 is None or len(df_bse50) == 0:
            df_bse50 = retry_fetch(ak.stock_zh_index_daily_em, symbol="bj899050")
        
        bse50_5d = 0
        if df_bse50 is not None and len(df_bse50) > 5:
            close_list = df_bse50['close'].astype(float).tolist()
            bse50_5d = (close_list[-1] - close_list[-6]) / close_list[-6] * 100

        spread_risk_on = c1000_20d - hs300_20d
        spread_defensive = div_20d - hs300_20d
        spread_fever = bse50_5d - c1000_5d

        results["dimensions"]["Activity"].update({
            "Style_RiskOn_20d_Spread_Pct": float(spread_risk_on),
            "Style_Defensive_20d_Spread_Pct": float(spread_defensive),
            "Style_BSE50_Fever_5d_Spread_Pct": float(spread_fever)
        })
        print(f"  -> 场内风格价差: 游资偏好(1000-300) {spread_risk_on:+.2f}% | 避险偏好(红利-300) {spread_defensive:+.2f}% | 极端妖风(北证50-1000) {spread_fever:+.2f}%")
    except Exception as e:
        print(f"  -> 场内风格价差获取异常: {e}")

except Exception as e:
    results["dimensions"]["Activity"]["error"] = str(e)
    print(f"  -> 活跃度获取异常: {e}")

# --- 保存 ---
output_path = os.path.join(OUTPUT_DIR, "cn_macro_4d.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=4)

print(f"\n✅ 数据全部抓取并组装完毕，安全导出至: {output_path}")


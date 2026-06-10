#!/usr/bin/env python3
"""
获取包含多周期涨跌幅的高频市场数据，输出JSON格式供P18使用
注意：数据由 fetch_high_freq_with_changes_v5.py 生成
"""

import pandas as pd
import json
import os
import glob
from datetime import datetime

def get_latest_high_freq_with_changes():
    """
    获取最新的包含多周期涨跌幅的高频数据
    """
    try:
        data_dir = "/root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/HighFreq_Monitor/highfreq_macro_data"
        json_files = glob.glob(os.path.join(data_dir, "high_freq_changes_*.json"))
        if not json_files:
            return None, "未找到高频数据文件，请先运行 fetch_high_freq_with_changes_v5.py"
        
        latest_json = max(json_files, key=os.path.getmtime)
        with open(latest_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data, None
    except Exception as e:
        return None, f"读取高频数据失败: {str(e)}"

def main():
    """主函数"""
    data, error = get_latest_high_freq_with_changes()
    
    if error:
        result = {
            "success": False,
            "error": error,
            "prices": {},
            "changes_1d": {},
            "changes_5d": {},
            "changes_20d": {},
            "changes_60d": {}
        }
    else:
        result = {
            "success": True,
            "timestamp": data.get("timestamp", ""),
            "prices": data.get("prices", {}),
            "changes_1d": data.get("changes_1d", {}),
            "changes_5d": data.get("changes_5d", {}),
            "changes_20d": data.get("changes_20d", {}),
            "changes_60d": data.get("changes_60d", {}),
            "macro_spreads": data.get("macro_spreads", {}),
            "is_trading_day": data.get("is_trading_day", True),
            "source": "high_freq_with_changes_multiduration"
        }
    
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
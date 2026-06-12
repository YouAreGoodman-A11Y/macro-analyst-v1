#!/usr/bin/env python3
"""
获取最新的中国 4D 宏观监控数据，输出 JSON 格式供 P20 使用
注意：数据由 fetch_cn_macro_4d.py 生成
"""

import json
import os
import glob

def get_latest_cn_macro_4d():
    try:
        data_dir = "/root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/HighFreq_Monitor/cn_macro_4d_data"
        json_files = glob.glob(os.path.join(data_dir, "cn_macro_4d*.json"))
        if not json_files:
            return None, "未找到 4D 宏观数据文件，请先运行 fetch_cn_macro_4d.py"
        
        latest_json = max(json_files, key=os.path.getmtime)
        with open(latest_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data, None
    except Exception as e:
        return None, f"读取 4D 宏观数据失败: {str(e)}"

def main():
    data, error = get_latest_cn_macro_4d()
    if error:
        print(json.dumps({"success": False, "error": error}, ensure_ascii=False))
    else:
        print(json.dumps(data, ensure_ascii=False))

if __name__ == "__main__":
    main()

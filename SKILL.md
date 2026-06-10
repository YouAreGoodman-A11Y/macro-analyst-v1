# 宏观研判流水线 SOP (Macro Pipeline V4.0)

> **触发暗号：** `更新宏观状态` / `进行宏观实盘推演`
> **适用模块：** Macro-Analyst-V1 根目录
> **版本：** V4.0 (双轨并进：全球宏观底色 + 中国本土流动性裂痕套利)

## ⚙️ 执行工作流

### Step 0: 准备三路数据源 (低频 + 全球高频 + 中国高频)
1. **低频基底 (过去基本面)**：深入 `Eyes/Macro_Data/` 或 `Eyes/Raw_Data/` 目录，读取**时间戳最新**的 JSON 宏观经济数据文件。
2. **全球外盘与大宗动量 (V5)**：运行脚本 `python3 /root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/scripts/fetch_high_freq_with_changes_v5.py` 提取最新多周期全球高频涨跌幅数据。
3. **中国本土流动性与微观结构 (4D)**：运行脚本 `python3 /root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/scripts/fetch_cn_macro_4d.py` 提取中国社融递推、DR007/Shibor、两融变动、场内风格价差等 A 股专属数据。

### Step 1: 【工序一】基本面法官 (P17_Macro_Scanner)
1. 调取 `Brain/references/v2_pipeline/P17_Macro_Scanner.md` 提示词。
2. **输入**：Step 0 拿到的**低频 JSON 数据**。
3. **任务**：严禁预测盘面。专心基于低频数据进行“宏观底色定性”，并强制输出一份**《盘面标准答案清单》**。
4. **输出**：《宏观基调设定与预期备忘录》（暂存于内存）。

### Step 2: 【工序二】全球高频批改助教 (P18_Macro_Phase)
1. 调取 `Brain/references/v2_pipeline/P18_Macro_Phase.md` 提示词。
2. **输入**：P17 的“标准答案清单” + **Step 0 提取的全球高频 V5 数据**（通过 `get_high_freq_with_changes.py` 读取）。
3. **任务**：完全摒弃主观偏见，拿着高频数据对 P17 的全球预期进行逐条批改。利用 HYG、RTY vs NDX、汇率、铜金比等验证全球信用与大宗真实性。
4. **输出**：《宏观高频盘面批改报告》及 YAML 全球状态机代码块。

### Step 3: 【工序三】中国本土流动性主理人 (P20_China_Macro_4D)
1. 调取 `Brain/references/v2_pipeline/P20_China_Macro_4D.md` 提示词。
2. **输入**：Step 0 提取的**中国 4D 宏观监控数据**（通过 `get_cn_macro_4d.py` 读取）。
3. **任务**：解构中国信用、金融流动性、内需通胀、微观活跃度(抱团价差/护盘ETF)。独立判断 A 股当前是“水牛”、“缩量防御”还是“信用牛”。
4. **输出**：《中国本土宏观与流动性洞察报告》及 YAML 中国状态机代码块、`China Liquidity JSON` 指令。

### Step 4: 【工序四】裂痕套利交易总司令 (P19_Macro_Action)
1. 调取 `Brain/references/v2_pipeline/P19_Macro_Action.md` 提示词。
2. **输入**：合并 P17(基本面)、P18(全球外盘)、P20(中国内盘) 的三份报告。
3. **任务**：发现中美周期背离，寻找全球理论与 A 股现实的**核心裂痕**。基于“盘面永远正确”原则，给出具体的 A 股结构配置红绿灯，并输出给强化学习模型的 `rl_parameters` JSON。
4. **输出**：最终版的《宏观大盘研判与实战策略报告》。

---

### 📂 最终归档动作
1. 将生成的 `P17`、`P18`、`P20` 中间思考记录保存至 `Brain/outputs/` 目录中。
2. 将 `P18` 和 `P20` 的 YAML 状态机代码块，分别覆写至 `State_Machine/宏观环境_状态机.md` 和 `State_Machine/中国盘面_状态机.md` 中。
3. 将 `P19` 的最终报告按格式保存至 `Reports/YYYY/MM/宏观洞察报告_YYYYMMDD_HHMMSS.md`。

至此，系统完成了一次融合全球视野与中国本土微观结构的顶级量化宏观推演。

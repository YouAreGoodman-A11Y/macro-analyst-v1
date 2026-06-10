# Brain/outputs 目录说明

## 目录结构
```text
Brain/outputs/
├── P17_Output_YYYYMMDD_HHMMSS.md    # P17 宏观基本面定调输出
├── P18_Output_YYYYMMDD_HHMMSS.md    # P18 全球高频盘面批改输出
├── P20_Output_YYYYMMDD_HHMMSS.md    # P20 中国本土宏观与流动性洞察输出
├── P17_Output_latest.md -> ...      # 最新P17符号链接
├── P18_Output_latest.md -> ...      # 最新P18符号链接
└── P20_Output_latest.md -> ...      # 最新P20符号链接
```

## 文件命名规范
- **P17_Output_YYYYMMDD_HHMMSS.md**: P17 基本面法官输出（低频理论定性）
- **P18_Output_YYYYMMDD_HHMMSS.md**: P18 全球高频批改输出（外盘大宗与汇率真实动量）
- **P20_Output_YYYYMMDD_HHMMSS.md**: P20 中国本土流动性输出（4D 数据内盘解构与风格抱团）
- 其中 `YYYYMMDD_HHMMSS` 为分析时间戳（如：20260610_103000）

## 自动保存机制
当执行宏观流水线推演时，Agent 应：
1. 依次生成带时间戳的 P17、P18 和 P20 的思考记录与中间输出文件。
2. 更新对应的 `*_latest.md` 符号链接指向最新生成的文件。
3. 统一集中保存至本目录。

## 相关文件流向与位置
- **P19 交易总司令报告 (最终合并产出)**: `../../Reports/YYYY/MM/宏观洞察报告_YYYYMMDD_HHMMSS.md`
- **状态机快照 (全系统的全局变量与真相源)**: 
  - `../../State_Machine/宏观环境_状态机.md` (P18 负责覆写更新)
  - `../../State_Machine/中国盘面_状态机.md` (P20 负责覆写更新)
- **核心分析协议 (Prompt 模板)**: `../references/v2_pipeline/` 
  - `P17_Macro_Scanner.md`
  - `P18_Macro_Phase.md`
  - `P20_China_Macro_4D.md`
  - `P19_Macro_Action.md`

## 使用示例
```bash
# 查看最新中国本土流动性洞察 (P20)
cat P20_Output_latest.md

# 查看特定日期的 P18 全球盘面输出
cat P18_Output_20260610_103000.md
```

## 历史记录
- 2026-04-23: 创建此目录，将 P17/P18 输出文件从 references 目录分离并迁移至此。
- 2026-06-10: 宏观研判架构全面升级至 V4.0。新增 P20（中国 4D 宏观与流动性主理人）独立输出流，彻底解耦全球宏观与中国本土 A 股特色逻辑。

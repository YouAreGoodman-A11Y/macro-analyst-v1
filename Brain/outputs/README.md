# Brain/outputs 目录说明

## 目录结构
```
Brain/outputs/
├── P17_Output_YYYYMMDD_HHMMSS.md    # P17宏观基调设定输出
├── P18_Output_YYYYMMDD_HHMMSS.md    # P18高频盘面批改输出
├── P17_Output_latest.md -> P17_Output_YYYYMMDD_HHMMSS.md  # 最新P17符号链接
└── P18_Output_latest.md -> P18_Output_YYYYMMDD_HHMMSS.md  # 最新P18符号链接
```

## 文件命名规范
- **P17_Output_YYYYMMDD_HHMMSS.md**: P17宏观基调设定输出
- **P18_Output_YYYYMMDD_HHMMSS.md**: P18高频盘面批改输出
- 其中 `YYYYMMDD_HHMMSS` 为分析时间戳（如：20260423_091500）

## 自动保存机制
当执行`更新宏观状态`命令时，系统会自动：
1. 生成带时间戳的P17和P18输出文件
2. 更新符号链接指向最新文件
3. 将文件保存到本目录

## 相关文件位置
- **P19报告**: `../Reports/YYYY/MM/宏观洞察应对报告_YYYYMMDD_HHMMSS.md`
- **状态机**: `../State_Machine/宏观环境_状态机.md`
- **分析模板**: `../references/v2_pipeline/` (P17_Macro_Scanner.md, P18_Macro_Phase.md, P19_Macro_Action.md)

## 使用示例
```bash
# 查看最新P17输出
cat P17_Output_latest.md

# 查看特定日期的P18输出
cat P18_Output_20260423_091500.md

# 查找所有P17输出
ls -la P17_Output_*.md
```

## 历史记录
- 2026-04-23: 创建此目录，将P17/P18输出文件从references目录迁移至此
- 2026-04-23: 建立自动保存机制，确保每次`更新宏观状态`都生成新文件
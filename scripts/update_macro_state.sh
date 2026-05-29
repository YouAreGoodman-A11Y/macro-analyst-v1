#!/bin/bash
# 宏观状态更新脚本
# 自动执行 P17 -> P18 -> P19 流程，并将输出保存到 Brain/outputs/

set -e

# 设置工作目录
WORKSPACE="/root/.openclaw/workspace-macro_analyst"
MACRO_DIR="$WORKSPACE/skills/Macro-Analyst-V1"
BRAIN_DIR="$MACRO_DIR/Brain"
OUTPUTS_DIR="$BRAIN_DIR/outputs"
REPORTS_DIR="$MACRO_DIR/Reports"
STATE_MACHINE_DIR="$MACRO_DIR/State_Machine"

# 创建必要的目录
mkdir -p "$OUTPUTS_DIR"
mkdir -p "$REPORTS_DIR/$(date +%Y)/$(date +%m)"
mkdir -p "$STATE_MACHINE_DIR"

# 生成时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_DIR=$(date +"%Y/%m")

echo "=== 开始宏观状态更新流程 (${TIMESTAMP}) ==="

# Step 0: 获取数据源
echo "Step 0: 获取数据源..."

# 1. 获取最新低频数据
LATEST_LOW_FREQ=$(find "$MACRO_DIR/Eyes/Macro_Data" -name "*.json" -type f | sort -r | head -1)
if [ -z "$LATEST_LOW_FREQ" ]; then
    echo "错误: 未找到低频数据文件"
    exit 1
fi
echo "低频数据: $(basename $LATEST_LOW_FREQ)"

# 2. 获取高频数据
echo "获取高频数据..."
HIGH_FREQ_JSON=$(python3 "$MACRO_DIR/scripts/get_high_freq_with_changes.py")
if [ $? -ne 0 ]; then
    echo "错误: 获取高频数据失败"
    exit 1
fi

# Step 1: P17_Macro_Scanner
echo "Step 1: 执行 P17_Macro_Scanner..."
P17_OUTPUT="$OUTPUTS_DIR/P17_Output_${TIMESTAMP}.md"

# 读取低频数据
LOW_FREQ_CONTENT=$(cat "$LATEST_LOW_FREQ")

# 创建P17分析（这里需要实际的分析逻辑，目前是示例）
cat > "$P17_OUTPUT" << EOF
# 宏观基调设定与预期备忘录 (P17)
**分析依据**：纯低频宏观数据 ($(date +"%Y-%m-%d %H:%M:%S"))

## 1. 宏观基本面底色 (低频定性)
*基于低频数据文件: $(basename $LATEST_LOW_FREQ)*

## 2. 盘面标准答案清单 (高频特征预期)
*注：实际分析需要更复杂的逻辑处理*
EOF

echo "P17输出已保存: $P17_OUTPUT"

# Step 2: P18_Macro_Phase
echo "Step 2: 执行 P18_Macro_Phase..."
P18_OUTPUT="$OUTPUTS_DIR/P18_Output_${TIMESTAMP}.md"

# 创建P18分析（这里需要实际的分析逻辑，目前是示例）
cat > "$P18_OUTPUT" << EOF
# 宏观高频盘面批改报告 (P18)
**验证依据**：高频多周期盘面数据 ($(date +"%Y-%m-%d %H:%M:%S"))

## 1. 逐条批改与验证打分
*基于高频数据进行分析*

## 2. 状态机更新快照
\`\`\`yaml
更新时间: "$(date +"%Y-%m-%d %H:%M")"
基础宏观底色: "待分析"
盘面验证总分: "0"
宏观与现实裂痕: "待分析"
全局战场性质: "待分析"
信用环境现况: "待分析"
市场广度现况: "待分析"
当前市场主线交易: "待分析"
\`\`\`
EOF

echo "P18输出已保存: $P18_OUTPUT"

# 更新状态机
STATE_MACHINE_FILE="$STATE_MACHINE_DIR/宏观环境_状态机.md"
cat > "$STATE_MACHINE_FILE" << EOF
\`\`\`yaml
更新时间: "$(date +"%Y-%m-%d %H:%M")"
基础宏观底色: "待分析"
盘面验证总分: "0"
宏观与现实裂痕: "待分析"
全局战场性质: "待分析"
信用环境现况: "待分析"
市场广度现况: "待分析"
当前市场主线交易: "待分析"
\`\`\`
EOF

# Step 3: P19_Macro_Action
echo "Step 3: 执行 P19_Macro_Action..."
P19_REPORT="$REPORTS_DIR/$DATE_DIR/宏观洞察应对报告_${TIMESTAMP}.md"

cat > "$P19_REPORT" << EOF
# 宏观大盘研判与实战策略报告 (P19)
**生成时间**: $(date +"%Y-%m-%d %H:%M")

## 一、裂痕套利主线与预期未来 (The Edge)
*基于P17和P18分析结果*

## 二、大类资产配置建议 (The Playbook)
*实际分析需要更复杂的逻辑处理*

## 三、动态剧本推演与风控阀门 (Scenario & Risk)
*实际分析需要更复杂的逻辑处理*
EOF

echo "P19报告已保存: $P19_REPORT"

# 创建符号链接到最新文件
ln -sf "$P17_OUTPUT" "$OUTPUTS_DIR/P17_Output_latest.md"
ln -sf "$P18_OUTPUT" "$OUTPUTS_DIR/P18_Output_latest.md"
ln -sf "$P19_REPORT" "$REPORTS_DIR/宏观洞察应对报告_latest.md"

echo "=== 宏观状态更新完成 ==="
echo "输出文件:"
echo "  - P17: $P17_OUTPUT"
echo "  - P18: $P18_OUTPUT"
echo "  - P19: $P19_REPORT"
echo "  - 状态机: $STATE_MACHINE_FILE"
echo "最新文件符号链接已创建"
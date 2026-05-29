#!/bin/bash
# 查找最新宏观报告脚本
# 用于反思时快速定位最新报告进行对比分析

REPORTS_DIR="/root/.openclaw/workspace-macro_analyst/skills/Macro-Analyst-V1/Reports"

echo "=== 查找最新宏观报告 ==="
echo "搜索目录: $REPORTS_DIR"
echo ""

# 查找所有报告文件
LATEST_REPORT=$(find "$REPORTS_DIR" -name "宏观洞察应对报告_*.md" -type f | sort -r | head -1)

if [ -z "$LATEST_REPORT" ]; then
    echo "❌ 未找到任何宏观报告"
    exit 1
fi

echo "✅ 最新报告: $LATEST_REPORT"
echo ""

# 显示报告基本信息
REPORT_NAME=$(basename "$LATEST_REPORT")
REPORT_DIR=$(dirname "$LATEST_REPORT")
REPORT_SIZE=$(du -h "$LATEST_REPORT" | cut -f1)
REPORT_TIME=$(stat -c %y "$LATEST_REPORT" | cut -d'.' -f1)

echo "📄 报告信息:"
echo "  - 文件名: $REPORT_NAME"
echo "  - 目录: $REPORT_DIR"
echo "  - 大小: $REPORT_SIZE"
echo "  - 修改时间: $REPORT_TIME"
echo ""

# 显示报告前10行（标题和生成时间）
echo "📋 报告摘要 (前10行):"
echo "--------------------------------------------------"
head -10 "$LATEST_REPORT"
echo "--------------------------------------------------"
echo ""

# 提供查看完整报告的命令
echo "🔍 查看完整报告:"
echo "  cat \"$LATEST_REPORT\""
echo ""

# 提供查找今日报告的命令
TODAY=$(date +%Y%m%d)
echo "📅 今日报告 ($TODAY):"
find "$REPORTS_DIR" -name "宏观洞察应对报告_${TODAY}*.md" -type f | sort -r | while read report; do
    echo "  - $(basename "$report")"
done

echo ""
echo "=== 查找完成 ==="
#!/bin/bash

# 租房协商前端启动脚本

echo "🏠 启动租房协商对话面板..."
echo "================================"

# 检查是否安装了 streamlit
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit 未安装"
    echo "正在安装依赖..."
    pip install -r requirements.txt
fi

# 检查后端API是否运行
echo "🔌 检查后端API连接..."
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ 后端API连接正常"
else
    echo "⚠️  后端API未运行，请先启动后端服务"
    echo "   在 backend 目录运行: python -m app.api_service.main"
fi

echo ""
echo "🚀 启动Streamlit前端..."
echo "📱 访问地址: http://localhost:8501"
echo "⏹️  停止服务: Ctrl+C"
echo ""

# 启动streamlit应用
streamlit run enhanced_negotiation_dashboard.py --server.port=8501 --server.address=0.0.0.0

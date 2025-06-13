#!/bin/bash

# 极简版启动脚本

echo "🏠 启动极简版租房协商演示..."

# 检查依赖
echo "📦 检查依赖..."
pip install streamlit requests > /dev/null 2>&1

# 启动应用
echo "🚀 启动前端应用..."
echo "📱 访问地址: http://localhost:8502"
streamlit run simple_test.py --server.port 8502 --server.address 0.0.0.0

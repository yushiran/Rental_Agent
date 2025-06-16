#!/bin/bash

# 启动修复版租房协商前端应用
echo "启动修复版租房协商前端应用..."
echo "确保后端服务已启动 (docker-compose up -d)"

# 启动Streamlit应用
streamlit run rental_app_fixed.py

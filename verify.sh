#!/bin/bash
# ============================================================
# PyHarness 验证脚本 (Linux/macOS)
# 在 Python 3.12+ 环境中运行此脚本
# ============================================================

echo "=========================================="
echo "PyHarness 验证流程"
echo "=========================================="
echo ""

echo "[1/5] 检查 Python 版本..."
python3 --version
echo ""

echo "[2/5] 安装依赖..."
pip install -e ".[dev]"
pip install cryptography
echo ""

echo "[3/5] 语法检查..."
echo "--- 源码文件 ---"
find src -name "*.py" -exec sh -c 'python3 -m py_compile "$1" && echo "[OK] $1" || echo "[FAIL] $1"' _ {} \;
echo "--- 测试文件 ---"
find tests -name "*.py" -exec sh -c 'python3 -m py_compile "$1" && echo "[OK] $1" || echo "[FAIL] $1"' _ {} \;
echo ""

echo "[4/5] 运行全部单元测试..."
pytest tests/ -v --tb=short
echo ""

echo "[5/5] 运行机制演示（三个确定性场景）..."
pytest tests/test_demo.py -v --tb=short
echo ""

echo "=========================================="
echo "验证完成"
echo "=========================================="
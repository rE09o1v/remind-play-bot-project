#!/bin/bash

# Render用のビルドスクリプト
# このスクリプトはRenderのデプロイ時に実行されます

echo "Installing system dependencies..."

# FFmpegのインストール（音楽再生に必要）
apt-get update && apt-get install -y ffmpeg

echo "Installing Python dependencies..."

# Pythonパッケージのインストール
pip install -r requirements.txt

echo "Build completed successfully!"

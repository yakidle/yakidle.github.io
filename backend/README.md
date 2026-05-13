# 智能论文讲解后端服务

## 环境依赖
- Python 3.8+
- pip install fastapi uvicorn python-pptx pymupdf

## 本地运行
```
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 主要接口
- POST `/upload` 上传论文PDF并返回分析与PPT下载链接
- GET `/ppt/xxx.pptx` 下载已生成PPT

> 建议部署到云服务器（如阿里云、腾讯云、VPS等），公网暴露（比如 http://你的IP:8000）。

## 修改 openai_api 调用
- 请将 main.py 里的 `call_chat_model` 替换为实际的大模型API
- 这里为了演示返回了模拟数据


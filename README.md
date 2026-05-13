# Paper PPT 理解与生成工具 - yakidle.github.io

该项目旨在实现一个网页版工具，帮助用户上传论文 PDF 文件，自动识别论文类型，利用大模型理解论文，输出汇报幻灯片内容，并智能提取关键图片（如模型结构图、overview 等）融合到 PPT 演示中。

---

## MVP（最小可用版本）功能

- 📄 支持 PDF 上传（前端解析）
- 🤖 支持展示自动讲解大纲/幻灯片内容（假数据，方便接入大模型API）
- 💬 讲解内容结构化输出，适合汇报
- 📝 代码结构清晰，易扩展对接后端或云端大模型

## 技术栈

- [React](https://reactjs.org/) + [Vite](https://vitejs.dev/) + TypeScript
- [PDF.js](https://mozilla.github.io/pdf.js/)（前端解析 PDF）
- 后端对接预留（推荐 OpenAI API、通义千问等）

## 使用指南

1. 访问[项目主页](https://yakidle.github.io/)。
2. 上传论文 PDF，页面自动解析展示内容（第一版为 mock 内容/示例，不上传也可体验）。
3. 后续计划支持自定义讲解、自动 PPTX 导出、智能插图等功能。

## 后续扩展建议
- 图片提取与 PPT 自动生成（需后端支持）
- 大模型 API 对接
- 多风格 PPT 支持
- 中/英文双语
- 交互优化和批注/答辩预测等

## 参考开源项目
- [ChatPaper](https://github.com/kaixindelele/ChatPaper)
- [paper2slides](https://github.com/tangjie1999/paper2slides)
- [python-pptx](https://github.com/scanny/python-pptx)

---

欢迎 star 和参与贡献！

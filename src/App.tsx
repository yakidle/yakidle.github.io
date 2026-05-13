import React, { useState } from 'react';

interface Slide {
  title: string;
  content: string;
  image?: string; // URL or base64
}

// 假数据，未来可用大模型API生成替换
const mockSlides: Slide[] = [
  {
    title: '论文简介',
    content: '本论文介绍了一种XXX的新方法，并聚焦于XXX领域的问题。',
  },
  {
    title: '核心方法框架',
    content: '下图展示了方法的整体框架架构。',
    image:
      'https://raw.githubusercontent.com/tangjie1999/paper2slides/main/static/images/architecture_example.png',
  },
  {
    title: '创新点',
    content: '1. xxx\n2. yyy\n3. zzz',
  },
  {
    title: '实验与分析',
    content: '方法在xxx任务上显著超越了SOTA。',
  },
  {
    title: '总结',
    content: '本工作提出的新方法在xxx方面取得明显提升，有望在yyy领域广泛应用。',
  },
];

function App() {
  const [slides, setSlides] = useState<Slide[]>(mockSlides);
  const [pdfName, setPdfName] = useState<string>('');
  const [pdfText, setPdfText] = useState<string>('');

  const handlePdfUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type === 'application/pdf') {
      setPdfName(file.name);
      // 这里只提取PDF名作演示，实际可用PDF.js前端解码内容，或者上传到后端服务器/云API。
      setPdfText('已上传PDF文件：' + file.name + '（演示用，暂不做内容解析）');
      // TODO: PDF内容解析后自动生成 slides，并setSlides
    } else {
      alert('请上传PDF格式的论文文件');
    }
  };

  return (
    <div style={{ fontFamily: 'Inter, Helvetica, Arial, sans-serif', maxWidth: 800, margin: '0 auto', padding: 24 }}>
      <h1>📝 论文组会PPT自动生成工具</h1>
      <p>上传论文PDF，一键生成汇报大纲和幻灯片（MVP演示版，内容为mock，未来可对接大模型智能解析）</p>
      <input type="file" accept="application/pdf" onChange={handlePdfUpload} />
      {pdfText && <div style={{ margin: '16px 0', color: '#555' }}>{pdfText}</div>}

      <h2>讲解幻灯片预览</h2>
      <div style={{display: 'flex', flexDirection: 'column', gap: 20}}>
        {slides.map((slide, idx) => (
          <div key={idx} style={{boxShadow:'0 2px 8px #eee',padding:18,borderRadius:12,background:'#fafcff'}}>
            <h3>{slide.title}</h3>
            <pre style={{whiteSpace:'pre-wrap',fontFamily:'inherit'}}>{slide.content}</pre>
            {slide.image && <img src={slide.image} alt="slide" style={{maxWidth:360,maxHeight:180, marginTop:10}}/>}
          </div>
        ))}
      </div>
      <div style={{marginTop:36, color:'#999',fontSize:12}}>前端采用 React+Vite，可二次开发特定风格PPT、对接大模型API、后端图片/公式提取。代码托管于 yakidle.github.io 仓库。</div>
    </div>
  );
}

export default App;

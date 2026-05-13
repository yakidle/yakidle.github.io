import React, { useState } from 'react';

const statusMap = [
  '正在上传论文…',
  '正在识别论文类型…',
  '正在总结内容、生成讲解…',
  '正在生成PPT文件…',
  '已完成！可以下载PPT文件。',
];

export default function UploadPaper() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<number>(-1);
  const [pptUrl, setPptUrl] = useState<string>('');
  
  // 这里将来换成实际后端API调用
  async function handleUploadMock(file: File) {
    for (let i = 0; i < statusMap.length; i++) {
      setStatus(i);
      await new Promise(resolve => setTimeout(resolve, 1000)); // 模拟每步1s
    }
    // 模拟输出 ppt 下载链接
    setPptUrl('/demo-group-ppt.pptx');
  }

  return (
    <div style={{ maxWidth: 500, margin: '60px auto', padding: 24, border: '1px solid #eee', borderRadius: 8, background: '#fafbfd' }}>
      <h2>论文组会PPT自动生成</h2>
      <p>上传你的论文PDF，系统将自动总结内容，判别类型，并输出讲解用PPT</p>
      <input
        type="file"
        accept="application/pdf"
        disabled={status >= 0 && status < statusMap.length - 1}
        onChange={e => {
          const file = e.target.files?.[0];
          setFile(file || null);
          setStatus(-1);
          setPptUrl('');
        }}
      />
      <br />
      {file && status === -1 && (
        <button
          onClick={() => handleUploadMock(file)}
          style={{ marginTop: 16, padding: '6px 18px', background: '#1975d1', color: '#fff', border: 'none', borderRadius: 4 }}
        >开始分析</button>
      )}
      {status >= 0 && (
        <div style={{ marginTop: 24, minHeight: 80 }}>
          <div>
            <b>{statusMap[status]}</b>
            <div style={{ width: 200, background: '#eee', height: 8, borderRadius: 4, overflow: 'hidden', margin: '18px 0' }}>
              <div style={{
                width: `${((status + 1) / statusMap.length) * 100}%`, background: '#2594f3', height: '100%'
              }} />
            </div>
          </div>
          {pptUrl && (
            <a href={pptUrl} download style={{ display: 'inline-block', marginTop: 8 }}>
              下载PPT
            </a>
          )}
        </div>
      )}
    </div>
  );
}

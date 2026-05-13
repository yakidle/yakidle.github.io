from flask import Flask, request, jsonify
from flask_cors import CORS

def fake_paper_analysis(file_storage):
    # 这里根据实际模型处理你的文件，下面为演示用
    filename = file_storage.filename
    return {
        "success": True,
        "paper_type": "演示论文",
        "summary": f"文件名为 {filename} ，这是后端返回的假摘要。\n请替换此部分为你的真实AI模型结果。",
        "ppt_url": None  # 或者生成后返回文件URL
    }

app = Flask(__name__)
CORS(app)

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf' not in request.files:
        return jsonify(success=False, message="未上传PDF文件。")
    pdf_file = request.files['pdf']
    # 这里调用实际的大模型推理/摘要函数
    try:
        result = fake_paper_analysis(pdf_file)
        return jsonify(result)
    except Exception as e:
        return jsonify(success=False, message=str(e))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

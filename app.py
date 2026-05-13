from flask import Flask, request, jsonify
from flask_cors import CORS

# 火山方舟豆包大模型的 AK/SK（你的密钥，勿泄露）
AK = "AKLTMDhmZmQ1Y2EyYmZkNDNjYmFjZDYwYzEyMDJjOGVkNjI"
SK = "WVRGaU4yTTBNbVpqTUdNeE5HVmtZamhtWWpFeE1UVmpNV1kyWTJNell6QQ=="
ENDPOINT = "maas-api.ml-platform-cn-beijing.volces.com"
MODEL = "moonshot-v1-8k"  # 推荐用 moonshot-v1-8k 或 doubao-2 具体看需要

# === 豆包大模型SDK（需要 pip install volcengine）===
try:
    from volcengine.maas.MaasService import MaasService
    svc = MaasService()
    svc.set_ak(AK)
    svc.set_sk(SK)
    svc.set_endpoint(ENDPOINT)
except ImportError:
    svc = None

app = Flask(__name__)
CORS(app)

@app.route('/model', methods=['POST'])
def model_ask():
    if svc is None:
        return jsonify(success=False, message="请先执行 pip install volcengine"), 500
    req = request.json
    user_input = (req.get('input') if req else '').strip()
    if not user_input:
        return jsonify(success=False, message='缺少 input'), 400
    try:
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": user_input}
            ]
        }
        resp = svc.chat_completions(payload)
        if "choices" in resp and len(resp["choices"]) > 0:
            return jsonify(result=resp["choices"][0]["message"]["content"])
        else:
            return jsonify(success=False, message='模型无回复'), 500
    except Exception as e:
        return jsonify(success=False, message=f'大模型请求失败: {e}'), 500

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf' not in request.files:
        return jsonify(success=False, message="未上传PDF文件。")
    pdf_file = request.files['pdf']
    filename = pdf_file.filename
    # 这里可以对接大模型做PDF摘要，这里只返回演示内容
    return jsonify({
        "success": True,
        "paper_type": "演示论文",
        "summary": f"文件名为 {filename} ，假摘要。如需接入大模型PDF理解，请补充实现。",
        "ppt_url": None
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

"""小鱼爱可可: pure-stdlib local web + GPT-SoVITS proxy + story library editor.

Stories are stored in docs/story-archive/ so they can be published via GitHub Pages.
The owner must still COMMIT/PUSH changed story files to update GitHub Pages.
"""
from __future__ import annotations

from collections import deque
import email.policy
import hmac
import io
import json
import mimetypes
import os
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import socket
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4
import wave

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
DATA = ROOT / 'data'
ARCHIVE = DOCS / 'story-archive'
AUDIO_DIR = ARCHIVE / 'audio'
CATALOG = ARCHIVE / 'catalog.json'
SETTINGS_PATH = Path(os.environ.get('XIAOYU_SETTINGS', ROOT / 'settings.local.json'))
VOICE_META = DATA / 'voice.json'
MAX_STORY_AUDIO = 24 * 1024 * 1024
MAX_VOICE_AUDIO = 12 * 1024 * 1024
MAX_BODY = 26 * 1024 * 1024
MAX_TEXT = 1200
MAX_OUTPUT = 48 * 1024 * 1024
MODEL_LOCK = threading.Lock()
STORY_LOCK = threading.Lock()
THROTTLE_LOCK = threading.Lock()
TTS_TIMES = deque()


def read_settings():
    if not SETTINGS_PATH.is_file():
        raise SystemExit('找不到 settings.local.json，请先双击 START_WINDOWS.bat 初始化。')
    cfg = json.loads(SETTINGS_PATH.read_text(encoding='utf-8-sig'))
    for key in ('admin_key', 'listener_key'):
        if not isinstance(cfg.get(key), str) or len(cfg[key]) < 16:
            raise SystemExit(f'{key} 缺失或太短，至少16字符。')
    origins = cfg.get('allowed_origins', [])
    if not isinstance(origins, list) or any(not isinstance(x, str) for x in origins):
        raise SystemExit('allowed_origins 应为字符串数组。')
    cfg['allowed_origins'] = origins
    url = os.environ.get('XIAOYU_SOVITS_URL', cfg.get('sovits_url', 'http://127.0.0.1:9880'))
    parts = urlsplit(url)
    if parts.scheme != 'http' or parts.hostname not in ('127.0.0.1', 'localhost') or parts.path not in ('', '/') or parts.query or parts.fragment or parts.username or parts.password:
        raise SystemExit('sovits_url 只能配置为本机 HTTP 地址，如 http://127.0.0.1:9880。')
    cfg['sovits_url'] = url.rstrip('/')
    return cfg


SETTINGS = read_settings()
DATA.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
if not CATALOG.is_file():
    CATALOG.write_text('{"stories": []}\n', encoding='utf-8')


def read_catalog():
    try:
        doc = json.loads(CATALOG.read_text(encoding='utf-8'))
        stories = doc.get('stories', [])
        if not isinstance(stories, list):
            return []
        return [s for s in stories if isinstance(s, dict) and re.fullmatch(r'[a-f0-9]{16}', s.get('id', ''))]
    except (ValueError, OSError, TypeError):
        return []


def save_catalog(stories):
    # Replace atomically so concurrent readers never see an incomplete catalog.
    data = json.dumps({'stories': stories}, ensure_ascii=False, indent=2) + '\n'
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=ARCHIVE, prefix='.catalog-', suffix='.tmp', delete=False) as f:
        f.write(data)
        temp = Path(f.name)
    temp.replace(CATALOG)


def voice_info():
    try:
        obj = json.loads(VOICE_META.read_text(encoding='utf-8'))
        if not re.fullmatch(r'voice\.(wav|mp3|flac)', obj['file']):
            return None
        if not (DATA / obj['file']).is_file():
            return None
        return obj
    except (FileNotFoundError, KeyError, ValueError, TypeError):
        return None


def model_alive():
    p = urlsplit(SETTINGS['sovits_url'])
    try:
        with socket.create_connection((p.hostname, p.port or 80), timeout=1.2):
            return True
    except OSError:
        return False


def parse_form(content_type, body):
    if not content_type.lower().startswith('multipart/form-data;'):
        raise ValueError('请使用 multipart/form-data 上传。')
    raw = b'MIME-Version: 1.0\r\nContent-Type: ' + content_type.encode('ascii', 'strict') + b'\r\n\r\n' + body
    message = BytesParser(policy=email.policy.default).parsebytes(raw)
    if not message.is_multipart():
        raise ValueError('上传内容格式不正确。')
    fields = {}
    for item in message.iter_parts():
        name = item.get_param('name', header='content-disposition')
        if not name or name in fields:
            raise ValueError('表单字段无效或重复。')
        fields[name] = (item.get_filename(), item.get_payload(decode=True) or b'')
    return fields


def get_field(fields, key, max_chars):
    if key not in fields:
        raise ValueError(f'缺少 {key} 字段。')
    value = fields[key][1].decode('utf-8').strip()
    if not 1 <= len(value) <= max_chars:
        raise ValueError(f'{key} 需要 1–{max_chars} 个字符。')
    return value


def validate_audio(filename, payload, *, voice=False):
    ext = Path(filename or '').suffix.lower()
    supported = {'.wav', '.mp3', '.flac'} if voice else {'.mp3', '.wav', '.m4a', '.ogg', '.webm', '.flac'}
    maxsize = MAX_VOICE_AUDIO if voice else MAX_STORY_AUDIO
    if ext not in supported:
        raise ValueError('音频格式不支持。建议使用 MP3；声音样本推荐 WAV。')
    if not payload or len(payload) > maxsize:
        raise ValueError(f'音频为空或超过 {maxsize // 1024 // 1024} MB。')
    if ext == '.wav':
        if payload[:4] != b'RIFF' or payload[8:12] != b'WAVE':
            raise ValueError('无效的 WAV 音频。')
        try:
            with wave.open(io.BytesIO(payload), 'rb') as f:
                duration = f.getnframes() / f.getframerate()
                if voice and not (2 <= duration <= 30):
                    raise ValueError('声音样本需 2–30 秒，推荐 5–10 秒。')
        except (wave.Error, ZeroDivisionError) as e:
            raise ValueError('WAV 格式无法读取，请使用 PCM WAV。') from e
    elif ext == '.mp3':
        if not (payload.startswith(b'ID3') or (len(payload) >= 2 and payload[0] == 255 and (payload[1] & 224) == 224)):
            raise ValueError('MP3 文件头不正确。')
    elif ext == '.flac' and not payload.startswith(b'fLaC'):
        raise ValueError('FLAC 文件头不正确。')
    elif ext in ('.m4a',) and payload[4:8] != b'ftyp':
        raise ValueError('M4A 文件头不正确。')
    elif ext == '.ogg' and not payload.startswith(b'OggS'):
        raise ValueError('OGG 文件头不正确。')
    elif ext == '.webm' and not payload.startswith(b'\x1a\x45\xdf\xa3'):
        raise ValueError('WebM 文件头不正确。')
    return ext


def split_text(text, limit=270):
    # Preserve paragraph/sentence punctuation and avoid sending huge requests to 8GB VRAM.
    bits = re.findall(r'[^。！？!?；;\n]+[。！？!?；;\n]*', text)
    if not bits:
        return [text]
    chunks, current = [], ''
    for bit in bits:
        while len(bit) > limit:
            if current:
                chunks.append(current)
                current = ''
            chunks.append(bit[:limit])
            bit = bit[limit:]
        if len(current) + len(bit) > limit and current:
            chunks.append(current)
            current = ''
        current += bit
    if current:
        chunks.append(current)
    return [c.strip() for c in chunks if c.strip()]


def call_model(text, speed, voice):
    payload = {
        'text': text, 'text_lang': 'zh', 'ref_audio_path': str((DATA / voice['file']).resolve()),
        'prompt_text': voice['prompt_text'], 'prompt_lang': 'zh', 'text_split_method': 'cut5',
        'batch_size': 1, 'speed_factor': speed, 'streaming_mode': False, 'media_type': 'wav',
        'parallel_infer': False, 'use_cuda_graph': False,
    }
    req = Request(SETTINGS['sovits_url'] + '/tts', data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(req, timeout=300) as r:
        ctype = r.headers.get('Content-Type', '')
        data = r.read(MAX_OUTPUT + 1)
    if not ctype.startswith('audio/') or len(data) > MAX_OUTPUT:
        raise ValueError('模型没有返回有效的 WAV 音频，请检查 api_v2.py 输出。')
    return data


def combine_wav(parts):
    """Combine same-format PCM wav chunks; if one chunk, return original data."""
    if len(parts) == 1:
        return parts[0]
    output = io.BytesIO()
    with wave.open(output, 'wb') as dest:
        expected = None
        for blob in parts:
            try:
                with wave.open(io.BytesIO(blob), 'rb') as src:
                    params = (src.getnchannels(), src.getsampwidth(), src.getframerate(), src.getcomptype())
                    if expected is None:
                        expected = params
                        dest.setnchannels(params[0]); dest.setsampwidth(params[1]); dest.setframerate(params[2])
                    elif expected != params:
                        raise ValueError('模型返回的音频参数不一致，无法合并。')
                    dest.writeframes(src.readframes(src.getnframes()))
            except wave.Error as e:
                raise ValueError('模型返回的 WAV 无法解析。') from e
            if output.tell() > MAX_OUTPUT:
                raise ValueError('故事较长，合成音频超过体积限制，请分段朗读。')
    return output.getvalue()


class Handler(BaseHTTPRequestHandler):
    server_version = 'XiaoyuKeke/1.0'

    def log_message(self, fmt, *args):
        # Do not print authorization headers or story contents.
        super().log_message(fmt, *args)

    def allowed_origin(self):
        origin = self.headers.get('Origin', '')
        if not origin:
            return True
        p = urlsplit(origin)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.path or p.query:
            return False
        if origin in SETTINGS['allowed_origins']:
            return True
        host = self.headers.get('Host', '')
        if origin in ('http://' + host, 'https://' + host):
            return True
        # cloudflared Quick Tunnel browser on its own matching host.
        return p.scheme == 'https' and p.hostname.endswith('.trycloudflare.com')

    def headers_out(self, ctype, size, status=200, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(size))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cache-Control', 'no-store')
        origin = self.headers.get('Origin', '')
        if origin and self.allowed_origin():
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type,X-Xiaoyu-Admin,X-Xiaoyu-Listener')
        if extra:
            for k, v in extra.items():
                self.send_header(k, v)
        self.end_headers()

    def send_json(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.headers_out('application/json; charset=utf-8', len(data), status)
        self.wfile.write(data)

    def require(self, role):
        if not self.allowed_origin():
            self.send_json(403, {'error': '网页来源未授权，请检查 allowed_origins。'})
            return False
        if role == 'admin':
            good = hmac.compare_digest(self.headers.get('X-Xiaoyu-Admin', ''), SETTINGS['admin_key'])
        else:
            candidate = self.headers.get('X-Xiaoyu-Listener', '')
            good = hmac.compare_digest(candidate, SETTINGS['listener_key']) or hmac.compare_digest(candidate, SETTINGS['admin_key'])
        if not good:
            self.send_json(401, {'error': '通行暗号不正确。' if role == 'listener' else '管理员密钥不正确。'})
            return False
        return True

    def body(self, maxsize=MAX_BODY):
        length = self.headers.get('Content-Length', '')
        if not length.isdigit() or not 0 < int(length) <= maxsize:
            raise ValueError('请求体为空、过大或格式不正确。')
        return self.rfile.read(int(length))

    def do_OPTIONS(self):
        if not self.path.startswith('/api/') or not self.allowed_origin():
            self.send_json(403, {'error': '不允许该来源。'})
            return
        self.headers_out('text/plain', 0, 204)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith('/api/'):
            if not self.allowed_origin():
                self.send_json(403, {'error': '不允许该来源。'}); return
            if path == '/api/status':
                self.send_json(200, {'service': True, 'app': 'xiaoyu-keke', 'model_api_reachable': model_alive(), 'voice_saved': bool(voice_info())}); return
            if path == '/api/stories':
                self.send_json(200, {'stories': read_catalog()}); return
            if path == '/api/admin/status':
                if not self.require('admin'): return
                v = voice_info()
                self.send_json(200, {'voice_saved': bool(v), 'prompt_text': v.get('prompt_text', '') if v else '', 'story_count': len(read_catalog())}); return
            self.send_json(404, {'error': '接口不存在。'}); return
        self.static_file(path)

    def static_file(self, path):
        if path in ('', '/'):
            path = '/index.html'
        elif path.endswith('/'):
            path += 'index.html'
        try:
            name = unquote(path)
            if '\\' in name or '\x00' in name:
                raise ValueError()
            file = (DOCS / name.lstrip('/')).resolve()
            if DOCS.resolve() not in file.parents or not file.is_file():
                raise ValueError()
            if file.suffix.lower() not in ('.html', '.css', '.js', '.json', '.png', '.jpg', '.jpeg', '.svg', '.mp3', '.wav', '.webm', '.m4a', '.ogg', '.flac', '.ico'):
                raise ValueError()
        except (ValueError, OSError):
            self.send_error(404); return
        types = {'.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.m4a': 'audio/mp4', '.webm': 'audio/webm', '.flac': 'audio/flac'}
        ctype = types.get(file.suffix.lower()) or mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        self.headers_out(ctype, file.stat().st_size)
        with file.open('rb') as inp:
            while True:
                part = inp.read(1024 * 1024)
                if not part: break
                self.wfile.write(part)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path == '/api/tts':
            if not self.require('listener'): return
        elif path in ('/api/admin/voice', '/api/admin/stories'):
            if not self.require('admin'): return
        else:
            self.send_json(404, {'error': '接口不存在。'}); return
        try:
            body = self.body()
            if path == '/api/tts': self.synthesize(body)
            elif path == '/api/admin/voice': self.upload_voice(body)
            else: self.upload_story(body)
        except (ValueError, UnicodeDecodeError) as e:
            self.send_json(400, {'error': str(e)})
        except HTTPError as e:
            detail = e.read(1200).decode('utf-8', 'replace')
            self.send_json(502, {'error': 'GPT-SoVITS 推理失败，请检查音频、参考文字和模型权重。', 'model_error': detail[:500]})
        except (URLError, TimeoutError) as e:
            self.send_json(504, {'error': '模型连接超时或已断开，请检查 GPT-SoVITS 后端。'})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print('Unhandled server error:', repr(e), flush=True)
            self.send_json(500, {'error': '服务处理失败，请查看服务窗口日志。'})

    def upload_voice(self, body):
        if not MODEL_LOCK.acquire(blocking=False):
            self.send_json(429, {'error': '模型繁忙，暂时不能更换声音样本。'}); return
        try:
            fields = parse_form(self.headers.get('Content-Type', ''), body)
            if 'audio' not in fields: raise ValueError('请选择参考录音。')
            name, audio = fields['audio']
            ext = validate_audio(name, audio, voice=True)
            prompt = get_field(fields, 'prompt_text', 200)
            target = DATA / ('voice' + ext)
            with tempfile.NamedTemporaryFile(dir=DATA, suffix=ext, prefix='.voice-', delete=False) as f:
                f.write(audio); tmp = Path(f.name)
            tmp.replace(target)
            with tempfile.NamedTemporaryFile('w', dir=DATA, encoding='utf-8', prefix='.meta-', suffix='.tmp', delete=False) as f:
                json.dump({'file': target.name, 'prompt_text': prompt, 'prompt_lang': 'zh'}, f, ensure_ascii=False)
                m = Path(f.name)
            m.replace(VOICE_META)
            for x in ('.wav', '.mp3', '.flac'):
                other = DATA / ('voice' + x)
                if other != target: other.unlink(missing_ok=True)
            self.send_json(200, {'ok': True, 'voice_saved': True})
        finally:
            MODEL_LOCK.release()

    def upload_story(self, body):
        fields = parse_form(self.headers.get('Content-Type', ''), body)
        if 'audio' not in fields: raise ValueError('请先录制或上传音频文件。')
        title = get_field(fields, 'title', 75)
        name, audio = fields['audio']
        ext = validate_audio(name, audio)
        desc = fields.get('description', (None, b''))[1].decode('utf-8').strip()
        if len(desc) > 280: raise ValueError('简介最多280个字。')
        with STORY_LOCK:
            ident = uuid4().hex[:16]
            filename = f'{ident}{ext}'
            dest = AUDIO_DIR / filename
            with tempfile.NamedTemporaryFile(dir=AUDIO_DIR, prefix='.record-', suffix=ext, delete=False) as f:
                f.write(audio); temp = Path(f.name)
            temp.replace(dest)
            record = {'id': ident, 'title': title, 'description': desc, 'audio': f'../story-archive/audio/{filename}', 'created_at': time.strftime('%Y-%m-%d', time.localtime())}
            records = read_catalog()
            try:
                save_catalog([record] + records)
            except Exception:
                dest.unlink(missing_ok=True)
                raise
        self.send_json(201, {'ok': True, 'story': record, 'publish_required': True})

    def synthesize(self, body):
        if not MODEL_LOCK.acquire(blocking=False):
            self.send_json(429, {'error': '小鱼正在读上一段文字，请稍后再试。'}); return
        try:
            now = time.monotonic()
            with THROTTLE_LOCK:
                while TTS_TIMES and now - TTS_TIMES[0] > 3600: TTS_TIMES.popleft()
                recent = sum(now - t < 60 for t in TTS_TIMES)
                if len(TTS_TIMES) >= 30 or recent >= 5:
                    self.send_json(429, {'error': '今天/这一分钟的语音合成请求有点多，请稍后再试。'}); return
                TTS_TIMES.append(now)
            try:
                request = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                raise ValueError('输入文字格式不正确。') from e
            text = request.get('text', '')
            if not isinstance(text, str) or not 1 <= len(text.strip()) <= MAX_TEXT:
                raise ValueError(f'请输入 1–{MAX_TEXT} 字的中文文字。')
            speed = request.get('speed', 1.0)
            if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not 0.75 <= speed <= 1.25:
                raise ValueError('语速应为 0.75–1.25。')
            voice = voice_info()
            if not voice:
                self.send_json(409, {'error': '还没有设置小鱼的声音，请管理员先保存自己的参考录音。'}); return
            if not model_alive():
                self.send_json(503, {'error': '小鱼的声音服务还没开启，请稍后再来。'}); return
            result = combine_wav([call_model(part, float(speed), voice) for part in split_text(text.strip())])
            if len(result) > MAX_OUTPUT:
                raise ValueError('音频太长，请拆成两段生成。')
            self.headers_out('audio/wav', len(result), extra={'Content-Disposition': 'attachment; filename="xiaoyu-story.wav"'})
            self.wfile.write(result)
        finally:
            MODEL_LOCK.release()

    def do_PUT(self):
        self.update_or_delete_story('PUT')

    def do_DELETE(self):
        self.update_or_delete_story('DELETE')

    def update_or_delete_story(self, method):
        path = urlsplit(self.path).path
        m = re.fullmatch(r'/api/admin/stories/([a-f0-9]{16})', path)
        if not m:
            self.send_json(404, {'error': '接口不存在。'}); return
        if not self.require('admin'): return
        try:
            edited = None
            if method == 'PUT':
                obj = json.loads(self.body(8 * 1024).decode('utf-8'))
                title = obj.get('title', '').strip()
                desc = obj.get('description', '').strip()
                if not isinstance(title, str) or not 1 <= len(title) <= 75: raise ValueError('故事标题要在1–75字之间。')
                if not isinstance(desc, str) or len(desc) > 280: raise ValueError('简介最多280字。')
            with STORY_LOCK:
                records = read_catalog()
                idx = next((i for i, s in enumerate(records) if s['id'] == m.group(1)), None)
                if idx is None:
                    self.send_json(404, {'error': '故事不存在。'}); return
                if method == 'DELETE':
                    entry = records.pop(idx)
                    save_catalog(records)
                    # Never use input paths for filesystem deletion; infer filename from fixed ID.
                    for ext in ('.mp3', '.wav', '.m4a', '.ogg', '.webm', '.flac'):
                        (AUDIO_DIR / (m.group(1) + ext)).unlink(missing_ok=True)
                else:
                    records[idx]['title'] = title
                    records[idx]['description'] = desc
                    edited = records[idx]
                    save_catalog(records)
            self.send_json(200, {'ok': True, 'story': edited, 'publish_required': True})
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
            self.send_json(400, {'error': str(e)})
        except Exception as e:
            print('Story update error:', repr(e), flush=True)
            self.send_json(500, {'error': '更新失败，请检查服务窗口日志。'})


def serve(host='127.0.0.1', port=7865):
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    print(f'小鱼爱可可本地网站: http://{host}:{port}', flush=True)
    print('故事后台: http://127.0.0.1:7865/admin/', flush=True)
    print('GPT-SoVITS API:', SETTINGS['sovits_url'], flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == '__main__':
    serve()

"""Integration checks without downloading GPT-SoVITS or using a GPU."""
import importlib.util
import io
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import wave

ADMIN = 'test_admin_secret_01234567890123456789'
LISTENER = 'test_listener_secret_01234567890123456'


def audio_wav(seconds=3):
    b = io.BytesIO()
    with wave.open(b, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(b'\0\0' * (8000 * seconds))
    return b.getvalue()


def multipart(fields, filekey=None, filename=None, data=None):
    boundary = 'xiaoyu-test-boundary'
    result = bytearray()
    for name, value in fields.items():
        result += (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode()
    if filekey:
        result += (f'--{boundary}\r\nContent-Disposition: form-data; name="{filekey}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()
        result += data + b'\r\n'
    result += f'--{boundary}--\r\n'.encode()
    return bytes(result), {'Content-Type': f'multipart/form-data; boundary={boundary}'}


class GatewayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        cls.tmp = tempfile.TemporaryDirectory(prefix='xiaoyu-test-')
        cls.base = Path(cls.tmp.name)
        for d in ('docs/beads', 'docs/story-archive/audio', 'server', 'data'):
            (cls.base / d).mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / 'server' / 'gateway.py'
        shutil.copyfile(source, cls.base / 'server' / 'gateway.py')
        (cls.base / 'docs' / 'index.html').write_text('homepage', encoding='utf-8')
        (cls.base / 'docs' / 'beads' / 'index.html').write_text('beadpage', encoding='utf-8')
        (cls.base / 'docs' / 'story-archive' / 'catalog.json').write_text('{"stories":[]}', encoding='utf-8')
        (cls.base / 'settings.local.json').write_text(json.dumps({
            'admin_key': ADMIN, 'listener_key': LISTENER,
            'allowed_origins': ['https://yakidle.github.io'], 'sovits_url': 'http://127.0.0.1:9880',
        }), encoding='utf-8')
        os.environ['XIAOYU_SETTINGS'] = str(cls.base / 'settings.local.json')
        spec = importlib.util.spec_from_file_location('gateway_test', cls.base / 'server' / 'gateway.py')
        cls.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.mod)
        cls.mod.model_alive = lambda: True
        cls.model_calls = []
        def fake_call(text, speed, voice):
            cls.model_calls.append((text, speed))
            return audio_wav(1)
        cls.original_call_model = cls.mod.call_model
        cls.mod.call_model = fake_call
        cls.srv = ThreadingHTTPServer(('127.0.0.1', 0), cls.mod.Handler)
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = 'http://127.0.0.1:' + str(cls.srv.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.tmp.cleanup()

    def request(self, path, method='GET', data=None, headers=None, origin=None):
        h = headers or {}
        if origin is not None: h['Origin'] = origin
        req = Request(self.origin + path, data=data, headers=h, method=method)
        try:
            with urlopen(req, timeout=5) as r:
                return r.status, r.read(), dict(r.headers)
        except HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def test_01_static_and_auth(self):
        code, content, _ = self.request('/')
        self.assertEqual((code, content), (200, b'homepage'))
        self.assertEqual(self.request('/beads/')[1], b'beadpage')
        self.assertEqual(self.request('/settings.local.json')[0], 404)
        self.assertEqual(self.request('/api/admin/status')[0], 401)
        self.assertEqual(self.request('/api/admin/status', headers={'X-Xiaoyu-Admin': LISTENER})[0], 401)
        self.assertEqual(self.request('/api/admin/status', headers={'X-Xiaoyu-Admin': ADMIN}, origin='https://bad.example')[0], 403)

    def test_02_voice_and_tts(self):
        body, h = multipart({'prompt_text': '今天天气真好。'}, 'audio', 'reference.wav', audio_wav())
        h['X-Xiaoyu-Admin'] = ADMIN
        code, raw, _ = self.request('/api/admin/voice', method='POST', data=body, headers=h)
        self.assertEqual((code, json.loads(raw)['voice_saved']), (200, True))
        body = json.dumps({'text': '今天天气真好！' * 100, 'speed': 1}).encode()
        self.assertEqual(self.request('/api/tts', 'POST', body, {'Content-Type': 'application/json'})[0], 401)
        code, raw, headers = self.request('/api/tts', 'POST', body, {'X-Xiaoyu-Listener': LISTENER, 'Content-Type': 'application/json'})
        self.assertEqual(code, 200)
        self.assertTrue(raw.startswith(b'RIFF'))
        self.assertGreater(len(self.model_calls), 1)
        self.assertEqual(headers['Content-Type'], 'audio/wav')

    def test_02b_current_voice_parameters(self):
        from unittest.mock import patch
        mod = self.mod
        self.assertEqual(mod.SETTINGS['tts_options']['speed'], 1.05)
        self.assertEqual(mod.SETTINGS['tts_options']['text_split_method'], 'cut1')
        self.assertEqual(mod.SETTINGS['tts_options']['top_k'], 35)
        captured = {}
        class FakeResponse:
            headers = {'Content-Type': 'audio/wav'}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit): return audio_wav(1)
        def capture(req, timeout=0):
            captured.update(json.loads(req.data))
            return FakeResponse()
        with patch.object(mod, 'urlopen', side_effect=capture):
            type(self).original_call_model('可可，听故事。', 1.05, {'file': 'voice.wav', 'prompt_text': '我想给你讲故事。'})
        self.assertEqual(captured['speed_factor'], 1.05)
        self.assertEqual(captured['fragment_interval'], 0.4)
        self.assertEqual(captured['top_k'], 35)
        self.assertEqual(captured['top_p'], 0.7)
        self.assertEqual(captured['temperature'], 0.7)
        self.assertEqual(captured['text_split_method'], 'cut1')

    def test_03_story_create_edit_remove(self):
        body, h = multipart({'title': '小鱼录的故事', 'description': '给可可的故事'}, 'audio', 'record.mp3', b'ID3' + b'\0' * 512)
        h['X-Xiaoyu-Admin'] = ADMIN
        code, raw, _ = self.request('/api/admin/stories', 'POST', body, h)
        self.assertEqual(code, 201)
        ident = json.loads(raw)['story']['id']
        self.assertEqual(len(ident), 16)
        code, raw, _ = self.request('/api/stories',origin='https://yakidle.github.io')
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)['stories'][0]['title'], '小鱼录的故事')
        audio = '/story-archive/audio/' + ident + '.mp3'
        self.assertTrue(self.request(audio)[1].startswith(b'ID3'))
        edit = json.dumps({'title': '改过的故事', 'description': '新的简介'}).encode()
        code, raw, _ = self.request('/api/admin/stories/'+ident, 'PUT', edit, {'X-Xiaoyu-Admin': ADMIN, 'Content-Type': 'application/json'})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(self.request('/api/stories')[1])['stories'][0]['title'], '改过的故事')
        self.assertEqual(self.request('/api/admin/stories/'+ident, 'DELETE', headers={'X-Xiaoyu-Admin': LISTENER})[0], 401)
        self.assertEqual(self.request('/api/admin/stories/'+ident, 'DELETE', headers={'X-Xiaoyu-Admin': ADMIN})[0], 200)
        self.assertEqual(json.loads(self.request('/api/stories')[1])['stories'], [])
        self.assertEqual(self.request(audio)[0], 404)

if __name__ == '__main__':
    unittest.main()

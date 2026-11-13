"""Local demo UI. Run: python -m starter.src.demo (no extra dependencies)."""
import argparse
import atexit
import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .provenance import local_source_path
from .corpus import load_multidoc_pages

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / 'starter/ui'


class DemoService:
    def __init__(self):
        self.lock = threading.Lock()
        self.embedder = None
        self.store = None
        self.hybrid = None

    def close(self):
        if self.store:
            self.store.close()
            self.store = None

    def summary(self):
        def read(path):
            return json.loads((ROOT / path).read_text(encoding='utf-8'))
        extension = read('results/extension/metrics.json') if (ROOT/'results/extension/metrics.json').exists() else {}
        vi = None
        if (ROOT/'results/vietnamese/metrics.json').exists():
            vi = dict(metrics=read('results/vietnamese/metrics.json'),statistics=read('results/vietnamese/statistics.json'),
                      questions=read('benchmark/vietnamese_questions.json'),manifest=read('data/vietnamese/manifest.json'))
        multidoc = None
        if (ROOT/'results/multidoc/metrics.json').exists():
            multidoc = dict(metrics=read('results/multidoc/metrics.json'),by_source=read('results/multidoc/by_source.json'),
                by_kind=read('results/multidoc/by_kind.json'),selection=read('results/multidoc/selection.json'),run=read('results/multidoc/run.json'),
                manifest=read('data/multidoc/manifest.json'),questions=read('benchmark/multidoc_questions.json')+[dict(q,split='diagnostic') for q in read('benchmark/vietnamese_questions.json')])
        return dict(multidoc=multidoc,vietnamese=vi,extension_metrics=extension,
                    extension_config=read('benchmark/extension_protocol.json') if extension else None,
                    holdout_questions=read('benchmark/extension_holdout.json') if extension else [],
                    strategies=list('ABCD') if extension else list('ABC'),
                    metrics=read('results/metrics.json'), statistics=read('results/statistics.json'),
                    selection=read('results/selection.json'), run=read('results/run.json'),
                    protocol=read('benchmark/protocol.json'), manifest=read('data/manifest.json'),
                    questions=read('benchmark/questions.json'), review=read('results/review_summary.json'),
                    live_index_exists=(ROOT / '.qdrant/meta.json').is_file())

    def traces(self, question_id, corpus='alice'):
        trace_path = ROOT/({'nd13':'results/vietnamese/traces.jsonl','multidoc':'results/multidoc/traces.jsonl'}.get(corpus,'results/traces.jsonl'))
        rows = [json.loads(line) for line in trace_path.read_text(encoding='utf-8').splitlines()]
        extension_path = ROOT/'results/extension/traces.jsonl'
        if corpus=='alice' and extension_path.exists():
            rows.extend(json.loads(line) for line in extension_path.read_text(encoding='utf-8').splitlines())
        matches = sorted([r for r in rows if r['id'] == question_id], key=lambda r:r['strategy'])
        for r in matches:
            r.pop('candidates', None)
        if not matches:
            raise ValueError('Không tìm thấy câu hỏi benchmark.')
        return matches

    def page(self, page, document='alice'):
        if document not in ('alice','nd13','nd69','nd42','sherlock'):raise ValueError('Unknown document')
        path=ROOT/('data/vietnamese/pages.json' if document=='nd13' else 'data/pages.json' if document=='alice' else 'data/multidoc/pages.json')
        pages = load_multidoc_pages(ROOT) if document in ('nd69','nd42','sherlock') else json.loads(path.read_text(encoding='utf-8'))
        matches = [p for p in pages if p['page'] == page and p.get('document_id', 'alice')==document]
        if not matches:
            raise ValueError('Không tìm thấy đơn vị nguồn.')
        return matches[0]

    def search(self, payload):
        question = payload.get('question')
        strategy = payload.get('strategy', 'C')
        chapter = payload.get('chapter', '')
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
            raise ValueError('Nhập câu hỏi từ 1 đến 2.000 ký tự.')
        if strategy not in ('A', 'B', 'C', 'D', 'all'):
            raise ValueError('Cấu hình không hợp lệ.')
        if chapter not in ('', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII'):
            raise ValueError('Chương không hợp lệ.')
        with self.lock:
            if not (ROOT / '.qdrant/meta.json').is_file():
                raise RuntimeError('Chưa có vector index. Chạy python -m starter.src.run trước. Bạn vẫn có thể xem benchmark đã lưu.')
            if self.embedder is None:
                from .embeddings import MyEmbedder
                from .store import QdrantStore
                embedder = MyEmbedder()
                store = QdrantStore(str(ROOT / '.qdrant'), embedder.dimensions)
                if not all(store.client.collection_exists(s) for s in 'ABC'):
                    store.close()
                    raise RuntimeError('Index chưa đủ A/B/C. Chạy pipeline trước khi demo trực tiếp.')
                self.embedder, self.store = embedder, store
            started = time.perf_counter()
            vector = self.embedder.embed_query(question.strip())
            results = []
            strategies = tuple('ABCD') if (ROOT/'results/extension/metrics.json').exists() else tuple('ABC')
            for s in strategies if strategy == 'all' else (strategy,):
                filters = {'chapter': chapter} if s in ('C','D') and chapter else None
                if s == 'D':
                    if self.hybrid is None:
                        from .hybrid import HybridRetriever
                        config = json.loads((ROOT/'benchmark/extension_protocol.json').read_text())
                        self.hybrid = HybridRetriever(self.store, config)
                    hits, _ = self.hybrid.search(question.strip(), vector, filters=filters)
                else:
                    hits = self.store.search(s, vector, filters=filters)
                results.append(dict(strategy=s, hits=hits, applied_filter=filters or {}))
            return dict(mode='live', question=question.strip(), results=results,
                        elapsed_ms=round((time.perf_counter()-started)*1000),
                        note='Truy xuất trực tiếp; không chấm Hit vì câu hỏi tự do không có gold.')


service = DemoService()
atexit.register(service.close)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        try:
            if parsed.path == '/api/summary':
                return self.send_json(service.summary())
            if parsed.path == '/api/multidoc/traces':
                return self.send_json(service.traces(parse_qs(parsed.query).get('id',[''])[0],corpus='multidoc'))
            if parsed.path == '/api/vi/traces':
                return self.send_json(service.traces(parse_qs(parsed.query).get('id', [''])[0],corpus='nd13'))
            if parsed.path in ('/source/nd13.pdf','/source/nd69.pdf','/source/nd42.pdf'):
                document=Path(parsed.path).stem
                manifest=json.loads((ROOT/'data/vietnamese/manifest.json').read_text()) if document=='nd13' else json.loads((ROOT/f'data/multidoc/{document}_manifest.json').read_text())
                source=local_source_path(ROOT,manifest)
                if not source.is_file():return self.send_json({'error':'Original PDF not available on this machine'},404)
                body=source.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type','application/pdf')
                self.send_header('Content-Length',str(len(body)))
                self.end_headers();self.wfile.write(body)
                return
            if parsed.path == '/api/traces':
                return self.send_json(service.traces(parse_qs(parsed.query).get('id', [''])[0]))
            if parsed.path == '/api/page':
                return self.send_json(service.page(int(parse_qs(parsed.query).get('id', ['0'])[0]),document=parse_qs(parsed.query).get('document',['alice'])[0]))
            files = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
            if parsed.path not in files:
                return self.send_json({'error': 'Not found'}, 404)
            filename, content_type = files[parsed.path]
            body = (UI / filename).read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)
        except (ValueError, KeyError) as exc:
            self.send_json({'error': str(exc)}, 400)
        except Exception:
            logging.exception('Demo GET failed')
            self.send_json({'error': 'Không đọc được artifacts. Kiểm tra terminal và chạy pipeline nếu thiếu dữ liệu.'}, 500)

    def do_POST(self):
        if self.path != '/api/search':
            return self.send_json({'error': 'Not found'}, 404)
        # UI is same-origin; reject browser requests from unrelated origins.
        origin = self.headers.get('Origin')
        if origin and origin != 'http://' + self.headers.get('Host', ''):
            return self.send_json({'error': 'Origin not allowed'}, 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16000:
                raise ValueError('Request quá lớn hoặc rỗng.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Yêu cầu JSON object.')
            self.send_json(service.search(data))
        except (ValueError, TypeError) as exc:
            self.send_json({'error': str(exc)}, 400)
        except Exception:
            logging.exception('Live retrieval failed')
            self.send_json({'error': 'Không truy xuất trực tiếp được. Kiểm tra terminal: model cần tải lần đầu; Qdrant chỉ cho một tiến trình mở index. Dừng pipeline/server khác rồi thử lại. Không dùng kết quả giả thay thế.'}, 503)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=18763)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'Data Ingestion Demo: http://127.0.0.1:{args.port}', flush=True)
    print('Ctrl+C để dừng. Dừng demo trước khi chạy lại pipeline (Qdrant local lock).', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.close()


if __name__ == '__main__':
    main()

# Pipeline đã hoàn thiện

Bản làm dùng **Qdrant local persistent + FastEmbed ONNX CPU**, không cần API key hoặc Docker.
Xem [README ở root](../README.md) để setup, chạy và đọc kết quả.

Từ root:

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.lock.txt
.venv/bin/python -m starter.src.run
.venv/bin/python -m unittest discover -s tests -v
```

Hoặc sau khi kích hoạt venv, từ thư mục `starter/`: `python -m src.run`.
`docker-compose.yml`, `init.sql` và `scripts/check_setup.py` được giữ làm tài liệu starter PostgreSQL ban đầu; không phải backend của thí nghiệm này.

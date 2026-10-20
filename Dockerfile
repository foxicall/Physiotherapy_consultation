# syntax=docker/dockerfile:1
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements-api.txt .
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements-api.txt; else pip install --no-cache-dir -r requirements-api.txt; fi
RUN useradd --create-home --uid 10001 clinic
COPY --chown=clinic:clinic server.py catalog.py consultation.py syndrome_kb.py clinic_info.json pt-50-syndromes-database.md ./
COPY --chown=clinic:clinic docs ./docs
USER clinic
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import os,urllib.request; urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:'+os.getenv('PORT','8000')+'/api/health',timeout=3)"
CMD ["sh", "-c", "exec uvicorn server:api --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]

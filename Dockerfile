FROM node:20-bookworm-slim AS hwpforge-runtime

WORKDIR /opt/hwpforge

RUN npm install --prefix /opt/hwpforge --omit=dev --no-audit --no-fund @hwpforge/mcp@0.5.0

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HWPX_EXPORT_ENGINE=auto

WORKDIR /app

COPY 02_main/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY 02_main/app ./app
COPY templates/style_guide.hwpx ./templates/style_guide.hwpx
COPY 02_main/templates/hwpx ./templates/hwpx
COPY 02_main/vendor ./vendor
COPY --from=hwpforge-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=hwpforge-runtime /opt/hwpforge ./vendor/hwpforge-mcp

EXPOSE 8000

CMD ["python", "-c", "import os; import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=int(os.getenv('PORT', '8000')))"]

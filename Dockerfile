FROM python:3.11-slim

WORKDIR /fast_api

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8002", "--workers", "4", "--forwarded-allow-ips", "*", "--proxy-headers", "api.main:app"]
FROM python:3.12.16-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt requirements-registry.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY catalog ./catalog
COPY migrations ./migrations
COPY scripts/provision_pool.py ./scripts/provision_pool.py
RUN useradd --uid 10001 --create-home amc
USER amc
RUN mkdir -m 700 /home/amc/mailbox
EXPOSE 8000
CMD ["uvicorn","app.main:app","--no-proxy-headers","--host","0.0.0.0","--port","8000"]

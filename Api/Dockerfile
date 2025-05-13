FROM python:3.10-slim
WORKDIR /app

COPY dependencias.txt .
RUN pip install --no-cache-dir -r dependencias.txt

COPY api.py .
COPY start.sh .
RUN chmod +x start.sh

EXPOSE 8000
CMD ["./start.sh"]

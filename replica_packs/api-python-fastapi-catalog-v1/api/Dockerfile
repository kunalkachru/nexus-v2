FROM python:3.11-slim

WORKDIR /app

RUN pip install fastapi uvicorn psycopg2-binary sqlalchemy

COPY api_server.py .

EXPOSE 8000

CMD ["python", "api_server.py"]

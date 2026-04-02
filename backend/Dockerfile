FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download es_core_news_sm

COPY app/ app/

CMD ["fastapi", "run", "app/main.py", "--port", "8000"]

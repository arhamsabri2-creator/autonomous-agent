FROM python:3.11-slim

# Force rebuild - cache bust v2
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN python -m playwright install --with-deps chromium

COPY . .

EXPOSE 7860

CMD ["python", "app.py"]
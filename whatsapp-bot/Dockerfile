FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY meta_errors.py .
COPY services ./services
COPY database ./database
COPY templates ./templates
COPY static ./static

EXPOSE 5100

CMD ["python", "app.py"]

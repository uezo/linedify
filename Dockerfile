FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=18080
EXPOSE 18080

CMD ["sh", "-c", "uvicorn examples.run:app --host 0.0.0.0 --port ${PORT}"]


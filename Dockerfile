FROM python:3.10-slim

ENV HTTP_PROXY=http://172.23.11.105:2002
ENV HTTPS_PROXY=http://172.23.11.105:2002

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN mkdir -p logs

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

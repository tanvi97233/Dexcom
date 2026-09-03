FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHROME_BINARY=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    BROWSER_HEADLESS=true \
    HOST=0.0.0.0 \
    PORT=10000

RUN apt-get update \
    && apt-get install --no-install-recommends -y chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 10000
CMD ["python", "app.py"]

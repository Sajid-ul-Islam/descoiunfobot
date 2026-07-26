FROM python:3.11-slim

# Install Bengali fonts for Plotly + Kaleido chart image rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-noto-extra \
    fonts-beng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["python", "bot.py"]

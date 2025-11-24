# Use Python 3.11 slim image
FROM python:3.11-slim

# 注意: Dockerコンテナ内ではUSBデバイスは通常使用できません
# 親機PCに直接接続されたNFCリーダーを使用する場合は、
# ホストPC上で直接Flaskを起動してください
# 
# libusbはnfcpyのインストールに必要ですが、
# コンテナ内では実際には動作しません
RUN apt-get update && \
    apt-get install -y libusb-1.0-0 libusb-1.0-0-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and resources
COPY app.py .
COPY static/ ./static/
COPY templates/ ./templates/

# Expose port
EXPOSE 5000

# Run Flask application
CMD ["python", "app.py"]

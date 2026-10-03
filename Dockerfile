FROM python:3.12-slim

# Install system dependencies required by OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

ENV OCR_LANGUAGE=en
ENV OCR_DEVICE=cpu
ENV MAX_FILE_SIZE_MB=10
ENV UPLOAD_DIR=uploads
ENV OUTPUT_DIR=outputs
ENV CORS_ORIGINS=https://document-ocr-ajaysah.vercel.app

RUN python -m pip install --upgrade pip
RUN python -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
RUN pip install -r requirements.txt

# Render assigns a port dynamically at runtime, but fallback to 10000 locally
ENV PORT=10000
EXPOSE ${PORT}

# Use shell form for CMD so it expands the $PORT environment variable correctly
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT

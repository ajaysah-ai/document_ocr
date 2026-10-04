FROM python:3.12-slim

# System dependencies required by OpenCV, PaddleOCR and FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1 \
    libglx-mesa0 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

VOLUME /app/uploads
VOLUME /app/outputs

ENV OCR_LANGUAGE=en \
    OCR_DEVICE=cpu \
    MAX_FILE_SIZE_MB=10 \
    UPLOAD_DIR=uploads \
    OUTPUT_DIR=outputs \
    CORS_ORIGINS=https://document-ocr-ajaysah.vercel.app

RUN python -m pip install --upgrade pip

# Install a stable PaddlePaddle version compatible with Python 3.12
RUN python -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/

# Install application dependencies
RUN python -m pip install --no-cache-dir -r requirements.txt

ENV PORT=10000

EXPOSE 10000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]

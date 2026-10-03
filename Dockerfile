FROM python:3.12-slim

# Install modern system dependencies required by OpenCV and PaddleOCR
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

ENV OCR_LANGUAGE=en
ENV OCR_DEVICE=cpu
ENV MAX_FILE_SIZE_MB=10
ENV UPLOAD_DIR=uploads
ENV OUTPUT_DIR=outputs
ENV CORS_ORIGINS=https://document-ocr-ajaysah.vercel.app/

RUN python -m pip install --upgrade pip
RUN python -m pip install paddlepaddle==3.3.0 -i https://paddlepaddle.org.cn
RUN pip install -r requirements.txt

ENV PORT=10000
EXPOSE ${PORT}

# Shell form lets Render bind its custom internal port variables dynamically
CMD uvicorn backend.main:app --host 0.0.0.0 --port $PORT

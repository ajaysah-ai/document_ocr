FROM python:3.12-slim

WORKDIR /app

COPY . .

ENV OCR_LANGUAGE=en
ENV OCR_DEVICE=cpu
ENV MAX_FILE_SIZE_MB=10
ENV UPLOAD_DIR=uploads
ENV OUTPUT_DIR=outputs

RUN python -m pip install --upgrade pip
RUN python -m pip install paddlepaddle==3.3.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
RUN pip install -r requirements.txt

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860", "--reload"]
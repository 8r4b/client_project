FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libgl1 \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install git+https://github.com/ageitgey/face_recognition_models
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
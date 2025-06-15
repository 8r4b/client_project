FROM python:3.12-slim

# Install system dependencies for dlib, face_recognition, OpenCV, and git
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

WORKDIR /app/backend

COPY requirements.txt .
RUN pip install --upgrade pip

# Install face_recognition_models directly from GitHub (downloads the models)
RUN pip install git+https://github.com/ageitgey/face_recognition_models

# Install the rest of your requirements
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
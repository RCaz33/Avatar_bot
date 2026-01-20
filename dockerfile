FROM python:3.12-slim AS builder

# bard setup
RUN apt-get update && apt-get install -y \
    git git-lfs ffmpeg libsm6 libxext6 cmake rsync libgl1 curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# install without gpu
RUN pip install --no-cache-dir -U pip
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# run
CMD ["python", "app.py"]
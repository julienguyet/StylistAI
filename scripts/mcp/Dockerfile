FROM python:slim-trixie

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip config set global.break-system-packages true

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app

RUN useradd -m -s /bin/bash appuser
USER appuser

EXPOSE 8001

CMD ["python", "main.py"]

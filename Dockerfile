# If you need to use an official Ubuntu base image: ubuntu:resolute-20251208
FROM nvidia/cuda:12.2.0-devel-ubuntu22.04 

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv git vim nano wget curl sudo \
    && rm -rf /var/lib/apt/lists/*

RUN pip config set global.break-system-packages true

# Create dev user
RUN useradd -m -s /bin/bash dev \
    && echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev \
    && chmod 0440 /etc/sudoers.d/dev

ENV HOME=/home/dev

# Set up a working directory
WORKDIR /workspace

USER dev

CMD ["/bin/bash"]

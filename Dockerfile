# If you need to use an official CUDA-enabled Ubuntu base image: nvidia/cuda:12.2.0-devel-ubuntu22.04
FROM ubuntu:resolute-20251208 

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv git vim nano wget curl sudo \
    && rm -rf /var/lib/apt/lists/*

# Set up a working directory
WORKDIR /workspace

RUN useradd -ms /bin/bash dev && usermod -aG sudo dev
USER dev

CMD ["/bin/bash"]

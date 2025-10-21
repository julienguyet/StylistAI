# 🧥 StylistAI: Your Personalized Fashion Recommender Agent
StylistAI is an intelligent recommendation system that combines deep learning and conversational AI to deliver personalized fashion advice.
It leverages customer profiles, purchase history, and product metadata to understand each user’s unique style.

The whole pipeline has been designed to be easily reproductible by leveraging Docker containers. Please refer to dedicated sections if you would like to reproduce.

## Dev Environment
The first thing we need is a dev environment. To do this we must (i) create a docker image and (ii) build the container.

### Docker Image
In a location of your choice, create a Dockerfile like in the below example. Please note you may have to adapt the image based on your GPU settings.

```
# Use an official CUDA-enabled Ubuntu base image
FROM nvidia/cuda:12.2.0-devel-ubuntu22.04

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
```

Then, in your terminal run:

```
docker build -t stylistai-dev /your/usr/path/to/docker/file
```

### Build Docker Container
In order to build the container you must in order: 
1. Clone this repo on your computer.
2. Create a dedicated data folder outside of the repo where to save needed files.

What we will do is create a container while mounting two volumes to it. Thus, we can work directly within the container while using our local storage.

Please note we are allocating port 9001 to our container but you can choose any that you like.

```
docker run -it --gpus all \
  -v your/path/to/folder/StylistAI:/workspace \
  -v your/path/to/folder/fashion_data:/data \
  -p 9001:9001 \
  --name stylistai-container \
  --restart always \
  stylistai-dev
```

Great! Now we are all set: to work from the container simply install the remote developer package in VS Code and look for the option "attach to running container" and you're good to go.

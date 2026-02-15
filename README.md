# 🧥 StylistAI: Your Personalized Fashion Recommender Agent
StylistAI is an intelligent recommendation system that combines deep learning and conversational AI to deliver personalized fashion advice.
It leverages customer profiles, purchase history, and product metadata to understand each user’s unique style.

The whole pipeline has been designed to be easily reproductible by leveraging Docker containers. Please refer to dedicated sections if you would like to reproduce.

## Dataset
Data has been retrieved from the *H&M Personalized Fashion Recommendations* competition hosted on [Kaggle](https://www.kaggle.com/competitions/h-and-m-personalized-fashion-recommendations/overview).

To recreate locally the databases you can refer to the dedicated sections below.

## Dev Environment
The first thing we need is a dev environment. To do this we must (i) create a docker image and (ii) build the container.

### Docker Image
In a location of your choice, create a Dockerfile like in the below example. Please note you may have to adapt the image based on your GPU settings.

```
# If you need to use an official CUDA-enabled Ubuntu base image: nvidia/cuda:12.2.0-devel-ubuntu22.04
FROM ubuntu:resolute-20251208 

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

Please note we are allocating port 9001 to our container but you can choose any that you like. You must also run all your containers on the same network. To do so you can run:
```
docker network create stylistai-net
```

Then you simply need to pass this network as an argument when building your containers.

```
docker run -it --gpus all `
  -v your/path/to/folder/StylistAI:/workspace `
  -v your/path/to/folder/fashion_data:/data `
  -p 9001:9001 `
  --network stylistai-net `
  --name stylistai-container `
  --restart always `
  stylistai-dev
```

Great! Now we are all set. To work from the container simply install the remote developer package in VS Code and look for the option "attach to running container" and you're good to go.

## MongoDB

```
docker run -d `
  --name stylistai-mongo `
  --network stylistai-net `
  -p 27017:27017 `
  -v C:\Users\guyet\Documents\mongo_data:/data/db `
  -e MONGO_INITDB_ROOT_USERNAME=admin `
  -e MONGO_INITDB_ROOT_PASSWORD=supersecurepassword `
  --restart always `
  mongo:7.0
```

## Recommender API

```
docker build -t recommender_api .
```

```
docker run -d --name stylistai-api --network stylistai-net -p 8000:8000 --restart always `
  -v "C:\Users\guyet\Documents\fashion_data:/data" `
  -e MODEL_PATH=/data/models/mlruns_outputs/fc49224e1ba24094ae6b606de6a86b17/saved_model `
  recommender_api
```

## MCP Server
```
fastmcp run main.py:mcp --transport http --port 8000
```

## Agent
```
adk create stylist_agent
```

```
adk web --port 8001
```

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

### MongoDB

To store our data we use a MongoDB instance. You can run the following command to start a MongoDB container with persistence and network configuration:

```powershell
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

`supersecurepassword` is a placeholder. Substitute your own, and use that same value in the
`MONGO_CONNECTION_STRING` of every service that talks to Mongo — the recommender API, the MCP
server, and the catalog API each read it from their own `.env`.

## Train Two Tower Model

### Model Definition

The recommendation system utilizes a **Two-Tower Architecture**, a standard for retrieval tasks in large-scale recommender systems.

- **Customer Tower**: Processes user features (ID, age, club status, fashion news frequency, etc.) and their purchase history to generate a user embedding.
- **Article Tower**: Processes item features (ID, product type, section, department, description, etc.) to generate an item embedding.

The model is trained to maximize the similarity (dot product) between the user embedding and the embedding of the article they purchased (positive pair), while minimizing similarity with other articles (in-batch negatives).

### Training Process

We have two ways to work with the model:

1.  **Experimentation (`notebooks/recommender_pooling.ipynb`)**: Use this Jupyter notebook for data exploration, feature engineering testing, and quick model prototyping. It allows for interactive debugging and visualization of data processing steps.
2.  **Production Training (`scripts/models/recommender.py`)**: This is the finalized script for training the model. It includes **MLflow** for experiment tracking (logging metrics, parameters, and artifacts like the saved model).

To launch a training run with MLflow tracking, run the script from your development environment. You can view the results by starting the MLflow UI:

```bash
mlflow server --port 5000
```

### Build API

Once the model is trained and saved, we serve it using a FastAPI application.

1.  **Build the API Docker image:**

```
docker build -t recommender_api .
```

```
docker run -d --name stylistai-api --network stylistai-net -p 8000:8000 --restart always `
  -v "C:\Users\guyet\Documents\fashion_data:/data" `
  -e MODEL_PATH=/data/models/mlruns_outputs/fc49224e1ba24094ae6b606de6a86b17/saved_model `
  recommender_api
```

## Vector Search

For the semantic catalog search we need two more containers: Ollama to compute the embeddings and Qdrant to store them.

```powershell
docker run -d --gpus=all --network stylistai-net -p 11434:11434 `
  -v ollama:/root/.ollama `
  --name ollama `
  ollama/ollama
```

Please note the `--gpus=all` flag only works if your machine has GPU passthrough. You can simply drop it otherwise.

Once the container runs, pull the embedding model we use:

```bash
docker exec ollama ollama pull embeddinggemma
```

A fresh Ollama container has no model at all, so this step is not optional. Then create the vector database:

```powershell
docker run -d --network stylistai-net -p 6333:6333 -p 6334:6334 `
  -v your/desired/path/to/qdrant/storage:/qdrant/storage `
  --name qdrant `
  --restart always `
  qdrant/qdrant
```

The `fashion_articles` collection is created and filled from `notebooks/create_embeddings.ipynb`, so you must run that notebook once before the catalog search can return anything.

Both containers must keep the names `ollama` and `qdrant` and stay on `stylistai-net`, as the MCP server calls them by those names.

## MCP Server

We use the Model Context Protocol (MCP) to expose our tools and data to the agent. The server hosts every tool Björn can call: recommendations, store lookup, semantic catalog search and the storefront controls described in the Storefront section below.

While developing you can run the server directly from the source tree. It then serves on `http://localhost:8001/mcp`:

```bash
cd scripts/mcp
python main.py
```

To build the image:

```bash
docker build -t mcp_server ./scripts/mcp
```

The server reads `MONGO_CONNECTION_STRING` from its own `.env` file. Please note it loads that file with `dotenv_values`, which reads the file itself and not the environment, so `--env-file` and `-e` have no effect here. The `.dockerignore` keeps your credentials out of the image, so we mount the file at run time instead:

```powershell
docker run -d --name mcp-server --network stylistai-net -p 8001:8001 --restart always `
  -v "${PWD}/scripts/mcp/.env:/app/.env:ro" `
  mcp_server
```

Run this from the repository root, as the mount path is relative to your working directory.

The container must be named `mcp-server` and run on `stylistai-net`. The agent connects to `http://mcp-server:8001/mcp`, and the tools themselves call the other services by container name (`stylistai-api`, `stylistai-catalog`, `qdrant` and `ollama`). None of these names resolve on the default bridge network.

If the container exits straight away with `KeyError: 'MONGO_CONNECTION_STRING'`, then the `.env` mount did not land. You can check with `docker logs mcp-server`. Because `--restart always` keeps it looping, remove it with `docker rm -f mcp-server` before trying again.

### Adding a new tool

The agent reads the tool list only once, when it starts. So after adding or editing a tool you must restart the MCP server first and the agent second, otherwise Björn keeps calling the old list:

```bash
docker restart mcp-server
docker restart stylist-agent
```

Two things are easy to forget here. The first is the `@mcp.tool` decorator, as without it the function is simply never registered. The second is `system_prompt.txt`, which is where you tell Björn when to use the tool. A registered tool with no rule in the prompt will never be called.

## Agent

The **Stylist Agent** is the conversational interface that interacts with the user. It uses the MCP server to fetch recommendations and product details.

To create the agent:

```bash
adk create stylist_agent
```

To quickly test and visualize the agent's behavior, use the `adk web` command. This launches a local web interface where you can chat with your agent and see its internal thought process:

```bash
adk web --port 8010
```

Please note we use port 8010 here and not 8001, which is already taken by the MCP server.

Once you are happy with the agent, you can serve it as an API in its own container:

```bash
docker build -t stylist_agent ./scripts/stylist_agent
```

```powershell
docker run -d --name stylist-agent --network stylistai-net -p 8015:8015 --restart always `
  stylist_agent
```

The image starts `adk api_server` on port 8015 and the container must be named `stylist-agent`, as this is the name the storefront uses to reach it. There is no `--env-file` to pass: ADK loads `scripts/stylist_agent/.env` on its own, which is where the `ANTHROPIC_API_KEY` lives.

Two things are worth knowing before you rebuild this one:

1.  **The system prompt is baked into the image.** The Dockerfile copies the whole folder, so editing `system_prompt.txt` changes nothing until you build again. You can confirm the new prompt landed with `docker exec stylist-agent cat /app/stylist_agent/system_prompt.txt`.
2.  **The dependencies are pinned on purpose.** They used to be free and a rebuild picked up a newer `google-adk` that no longer installs the `mcp` package. The import of `McpToolset` then fails and the agent never loads. Bump `scripts/stylist_agent/requirements.txt` deliberately rather than by accident.

## Storefront

On top of the chat interface, the project ships a full e-commerce front end so customers can browse the catalog *and* let the agent browse it for them.

### Catalog & Cart API

A FastAPI service that exposes the product catalog, the product images and a persistent cart stored in a `carts` collection in Mongo. It is the backend both the storefront and the agent's MCP tools talk to.

```bash
docker build -t catalog_api ./scripts/catalog_api
```

This service reads its configuration from the environment. The `.env` file is excluded from the image by `.dockerignore`, so the credentials have to be supplied at run time. Create the file once from the template:

```bash
cp scripts/catalog_api/.env.example scripts/catalog_api/.env
```

Then edit it and set `MONGO_CONNECTION_STRING` to the password your Mongo container uses. Please leave the values unquoted, as Docker passes quotes through literally rather than stripping them and this would corrupt the connection string.

```powershell
docker run -d --name stylistai-catalog --network stylistai-net -p 8002:8002 --restart always `
  -v "C:\Users\guyet\Documents\fashion_data:/data" `
  --env-file scripts/catalog_api/.env `
  catalog_api
```

Run this from the repository root, as `--env-file` resolves relative to your working directory.

Interactive API docs are then available at `http://localhost:8002/docs`.

If startup fails with `pymongo.errors.OperationFailure: Authentication failed`, the connection string does not match the credentials your Mongo container was created with. Remove the container with `docker rm -f stylistai-catalog` before correcting the value, otherwise `--restart always` keeps it retrying.

Finally, please note the H&M dataset has no price column, so the API generates a stable synthetic price per article (see `scripts/catalog_api/pricing.py`). It is a demo placeholder and not real H&M pricing.

### Web App

A Next.js storefront with catalog, product and cart pages, plus a chat panel on every page. All traffic to the catalog API and to the agent goes through Next.js route handlers, so no internal hostname is ever exposed to the browser.

To work on it locally:

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

The app is then available on `http://localhost:3000`. Edit `.env.local` to point `CATALOG_API_URL` and `ADK_API_URL` at your services.

Or build the container:

```bash
docker build -t stylistai-frontend ./frontend
```

```powershell
docker run -d --name stylistai-frontend --network stylistai-net -p 3000:3000 --restart always `
  -e CATALOG_API_URL=http://stylistai-catalog:8002 `
  -e ADK_API_URL=http://stylist-agent:8015 `
  stylistai-frontend
```

Please note the storefront is compiled at image build time, so any change to the front end code needs a new `docker build` before you can see it.

There is no login. On first visit the app offers a handful of real profiles sampled from the customer collection, and the chosen `customer_id` drives both the cart and the recommendations. It is also seeded into the agent session state, which is how Björn knows who he is talking to without ever asking for a 64 character hash.

### Mobile Web App

`frontend-mobile` is a vertical, phone shaped version of the same storefront. It is a separate Next.js app rather than a responsive tweak, so the desktop one keeps working exactly as it does today and both can run side by side.

The data layer is the same in both. The API route handlers and everything in `lib` are identical copies, so the `ui_action` contract behaves the same way and no MCP tool or prompt needs to change. Only the presentation differs: the whole app is one phone width column, navigation moves to a bottom bar, the chat becomes a full height sheet, and the product page stacks with a sticky add to cart bar.

Two behaviours are specific to this version. The chat sheet closes itself when Björn returns a `navigate` action, because on a phone the sheet covers the whole screen and a navigation you cannot see is a navigation that did not happen. It stays open on `cart_updated`, as the badge behind it refreshes on its own.

To work on it locally:

```bash
cd frontend-mobile
cp .env.local.example .env.local
npm install
npm run dev
```

The app is then available on `http://localhost:3001`. We use port 3001 on purpose so it does not clash with the desktop storefront on 3000.

Or build the container:

```bash
docker build -t stylistai-frontend-mobile ./frontend-mobile
```

```powershell
docker run -d --name stylistai-frontend-mobile --network stylistai-net -p 3001:3001 --restart always `
  -e CATALOG_API_URL=http://stylistai-catalog:8002 `
  -e ADK_API_URL=http://stylist-agent:8015 `
  stylistai-frontend-mobile
```

To record a vertical demo, the simplest way is to open Chrome DevTools, turn on the device toolbar and pick an iPhone. You then get a real 9:16 frame with the safe area insets applied. Resizing the browser window to roughly 500px wide works too, as the column fills anything narrower than 520px edge to edge. On a wider screen it centres itself instead and the grey background shows on either side, which looks like a device on a stage but is not a full bleed vertical video.

See `frontend-mobile/README.md` for the full list of what differs between the two versions.

### Letting the agent drive the UI

Any MCP tool can steer the storefront by including a `ui_action` object in its return value. The chat widget scans every tool response for it, and then navigates, refreshes the cart or shows a product grid accordingly:

```json
{"ui_action": {"type": "navigate", "path": "/product/108775015"}}
```

This is what turns a recommendation into an open product page. After changing a tool you can check your payload still parses:

```bash
cd frontend
npm run verify:ui-actions
```

See `scripts/mcp/TOOL_DESIGN_NOTES.md` for the API reference, the full `ui_action` contract and the design decisions involved in adding those tools.

## Running the Full Stack

Once every image is built, this is the order to start the containers. Each one only depends on the ones above it:

| Service | Container name | Port |
|---|---|---|
| MongoDB | `stylistai-mongo` | 27017 |
| Ollama | `ollama` | 11434 |
| Qdrant | `qdrant` | 6333 |
| Recommender API | `stylistai-api` | 8000 |
| Catalog & Cart API | `stylistai-catalog` | 8002 |
| MCP Server | `mcp-server` | 8001 |
| Stylist Agent | `stylist-agent` | 8015 |
| Storefront | `stylistai-frontend` | 3000 |
| Storefront (mobile) | `stylistai-frontend-mobile` | 3001 |

The names matter as much as the ports, since every service calls the others by container name on `stylistai-net`. If a tool fails with `Name or service not known`, then the container it is trying to reach is either stopped or not on that network. You can list what shares the network with:

```bash
docker network inspect stylistai-net --format '{{range .Containers}}{{.Name}} {{end}}'
```

Then open `http://localhost:3000`, pick a demo shopper, open the chat and ask for a recommendation. If Björn answers correctly but the store does not move, the reply reached you and the `ui_action` did not: have a look at the browser Network tab on `POST /api/chat` and check that `uiActions` is not empty in the response.

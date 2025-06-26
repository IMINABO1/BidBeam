# Real-Time Market Data Streamer

## Overview

This project implements a real-time market data streaming and visualization system. It demonstrates a full-stack architecture for capturing, processing, and displaying live order book data, simulating a high-throughput financial data feed.

The system comprises three main components:

1. A **gRPC**-based backend server simulating market data
2. A **FastAPI** web application acting as a bridge to stream this data via WebSockets
3. A frontend user interface for real-time visualization of order books

## Features

* **Simulated Market Data**

  * A gRPC server generates dynamic, simulated order book snapshots and incremental updates for multiple financial instruments.
* **High-Performance Data Transfer**

  * Utilizes gRPC for efficient, low-latency communication between the market data server and the FastAPI bridge.
* **Real-time Web Streaming**

  * Leverages WebSockets to push live market data updates from the FastAPI backend to connected web clients.
* **In-Memory Order Book Reconstruction**

  * Both the CLI client and the FastAPI bridge maintain an accurate, reconstructed order book state from received snapshots and updates.
* **Dynamic Web Visualization**

  * A clean, responsive web interface displays live order book depth for selected instruments.
* **Modular Architecture**

  * Clear separation of concerns between data generation, data bridging, and presentation layers.

## Architecture

```
+---------------------+      gRPC      +---------------------+      WebSocket      +------------------+
| Market Data Server  |<-------------->| FastAPI Web Bridge  |<------------------->| Web Browser (UI) |
| (backend/market_data_server.py)       | (frontend/main.py)  |                     | (index.html, JS, CSS)
| - Generates simulated data  ^         | - gRPC Client       |                     | - Connects to WS
| - Provides gRPC service     |         | - WebSocket Server  |                     | - Renders Order Books
+---------------------+       |         | - In-memory Order Book |                  +------------------+
                              |         |   Reconstruction    |
                              |         +---------------------+
                              |
                              +-------------------------------------+
                                 gRPC Connection for CLI Client
                                 (backend/market_data_client.py)
```

### Components

**Market Data Server (`backend/market_data_server.py`)**

* A gRPC server that simulates live order book data for various instruments.
* Sends initial snapshots and continuous incremental updates.

**FastAPI Web Bridge (`frontend/main.py`)**

* Acts as a gRPC client, subscribing to the Market Data Server.
* Maintains an in-memory representation of the order books.
* Exposes a WebSocket endpoint (`/ws/market_data/{instrument_id}`) for web clients.
* Broadcasts JSON-formatted order book state to all connected clients upon updates.

**Web Browser (Frontend)**

* Connects to the FastAPI WebSocket endpoint using JavaScript.
* Receives JSON-formatted order book data.
* Dynamically updates the HTML to display bids and asks in real time.

**CLI Client (`backend/market_data_client.py`) (Optional)**

* A simple command-line gRPC client for testing.
* Subscribes to the Market Data Server and prints order book updates to the console.

## Getting Started

### Prerequisites

* **Python** ≥ 3.8
* **pip** (Python package installer)
* **venv** (Python virtual environment)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/real-time-market-data.git  # replace with your repo URL
cd real-time-market-data
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate Protobuf Files

```bash
python -m grpc_tools.protoc \
  -I. \
  --python_out=backend \
  --pyi_out=backend \
  --grpc_python_out=backend \
  backend/market_data.proto
```

This creates `market_data_pb2.py` and `market_data_pb2_grpc.py` in `backend/market_data_pb2_generated/`.

### 5. Run the Market Data Server

```bash
# In a new terminal (with venv activated)
python -m backend.market_data_server
```

### 6. Run the FastAPI Web Bridge

```bash
# In another new terminal (with venv activated)
uvicorn frontend.main:app --reload
```

### 7. Access the Web Interface

Open your browser and navigate to:

```
http://localhost:8000/
```

You should see the real-time market data dashboard.

## Project Structure

```
.
├── backend/
│   ├── market_data.proto
│   ├── market_data_server.py
│   ├── market_data_client.py
│   ├── market_data_model.py
│   └── market_data_pb2_generated/
│       ├── __init__.py
│       ├── market_data_pb2.py
│       └── market_data_pb2_grpc.py
├── frontend/
│   ├── main.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── style.css
│       └── script.js
└── requirements.txt
```

## Technologies Used

* **Core**: Python 3.9+
* **RPC Framework**: gRPC
* **Web Framework**: FastAPI
* **ASGI Server**: Uvicorn
* **Templating**: Jinja2
* **Real-time Communication**: WebSockets
* **Frontend**: HTML, CSS, JavaScript

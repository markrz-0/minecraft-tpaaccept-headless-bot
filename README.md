# Headless TCP Network Client (Minecraft 1.21)

A lightweight, purely asynchronous Python bot that implements targeted segments of the Minecraft 1.21 TCP protocol. Built from scratch with **zero external dependencies**, this client manually handles raw TCP streams, byte-level packet parsing, and multi-stage cryptographic handshakes.

## ⚙️ Technical Highlights
* **Zero Dependencies:** Relies entirely on the Python Standard Library (`socket`, `zlib`, `struct`, `queue`, `threading`).
* **Raw Stream Parsing:** Implements a custom buffer-slicing algorithm to accurately reconstruct fragmented VarInts and packet data from continuous TCP streams.
* **Thread-Safe Architecture:** Utilizes the Producer-Consumer pattern (`queue.Queue`) to separate the incoming I/O listener thread from the outgoing execution loop, eliminating race conditions.
* **Dockerized:** Fully containerized for instant, isolated deployment.

## 🛠️ Architecture
The core system is split into two primary components:
1. **The Protocol handler (`Protocol_1_21`):** Manages the `socket` connection, Zlib compression thresholds, VarInt packing/unpacking, and multi-stage authentication (Handshake -> Login -> Config -> Play).
2. **The Event Loop (`TPAProtocol`):** A threaded implementation that asynchronously listens for keep-alives, position updates, and chat events, dispatching thread-safe automated responses.

## 🚀 Quick Start
```bash
# Clone the repo
git clone https://github.com/markrz-0/minecraft-tpaaccept-headless-bot.git
cd minecraft-tpaaccept-headless-bot

# Run via Docker
docker build -t tcp-bot .
docker run -e IP="127.0.0.1" -e PORT="25565" -e MCNAME="TestBot" tcp-bot
```

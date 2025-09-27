# Terminal Chat App (Python + asyncio)

## Description
This project implements a multi-user terminal chat system using Python 3 and asyncio.  
It includes two main components:

- **Server (`server.py`)**: receives connections from multiple clients, manages nicknames, public and private messages, and events. It displays everything happening in the console (connections, commands, messages, errors) and can optionally save the entire session to a file.  
- **Client (`client.py`)**: terminal application that allows connecting to the server, choosing a nickname, and participating in the chat in real time.  

The chat runs over pure TCP (not HTTP), making it lightweight, fast, and easy to use on local networks or over the Internet (with a public IP or VPS).  

---

## Usage

### Server
By default, it listens on 0.0.0.0:5555.

- Run without saving session:
```bash
./server.py
```

- Run and save everything to a file (JSON Lines):
```bash
./server.py --save chat_session.jsonl
```

The server always shows events in the terminal, and if `--save` is used, it also logs them to the specified file.

### Client
Connect to a server:
```bash
./client.py --host 127.0.0.1 --port 5555 --nick MrLaction
```

- `--host`: server IP (e.g., `192.168.0.10` on LAN or a VPS public IP).  
- `--port`: server port (default is 5555).  
- `--nick`: initial nickname (optional, can also be set with `/nick`).  

Example with two clients on the same machine:
```bash
./client.py --host 127.0.0.1 --port 5555 --nick MrLaction1
./client.py --host 127.0.0.1 --port 5555 --nick MrLaction2
```

---

## Available Commands
Inside the client, you can use:

- **`/nick <name>`** → Set or change nickname.  
- **`/list`** → Show list of connected users.  
- **`/msg <user> <text>`** → Send a private message to a user.  
- **`/me <action>`** → Send an action message (e.g., `/me waves`).  
- **`/quit`** → Disconnect from the chat.  
- **`/help`** → Show command help.  

Any text typed without `/` is sent to the public chat.

---

## Internal Functioning

### Server flow
1. Accepts TCP connections on port 5555.  
2. Sends a welcome message to each client.  
3. Handles commands (`/nick`, `/list`, `/msg`, etc.) and normal messages.  
4. Broadcasts public messages to all clients.  
5. Logs absolutely everything to the console and, if enabled, to file.  
6. Handles disconnections and automatically cleans up users.  

### Client flow
1. Opens a TCP connection to the server.  
2. Launches two tasks:  
   - One reads the keyboard and sends messages/commands.  
   - The other listens to the server and displays incoming messages.  
3. Keeps the session active until the user types `/quit` or the server closes the connection.  

---

## Network Scenarios
- **LAN/WiFi local**: all clients on the same network → use server’s private IP (`192.168.x.x`).  
- **Internet (remote)**:  
  - Server with public IP or VPS.  
  - Port 5555 open on firewall/router.  
  - Clients connect using the server’s public IP.  

---

## Session Logging
- In console: always shown in real time.  
- In file (`--save`): stored in JSON Lines format (`.jsonl`), ideal for analysis with `jq`, Python, or logging systems.  

Example:
```json
{"ts": "2025-09-26T23:00:00Z", "level": "INFO", "msg": "Nick set", "meta": {"new": "MrLaction"}}
{"ts": "2025-09-26T23:00:05Z", "level": "INFO", "msg": "Public message", "meta": {"from": "MrLaction", "len": 12, "preview": "Hello everyone"}}
```

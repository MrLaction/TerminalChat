#!/usr/bin/env python3
import asyncio
import argparse
import logging
import json
from datetime import datetime

WELCOME = (
    "Welcome to AsyncChat!\n"
    "Type /help for commands.\n"
    "First, set your nickname with: /nick <name>\n"
)

HELP = (
    "\nCommands:\n"
    "/nick <name>       Set or change your nickname\n"
    "/list              List connected users\n"
    "/msg <user> <txt>  Send a private message\n"
    "/me <action>       Emote (e.g., /me waves)\n"
    "/quit              Disconnect\n"
)

def setup_logger(save_path: str | None) -> logging.Logger:
    """
    Always logs to console. If save_path is provided, duplicates
    everything to that file as JSON Lines and keeps console text logs.
    """
    logger = logging.getLogger("chat")
    logger.setLevel(logging.DEBUG)  # capture everything
    logger.handlers.clear()
    logger.propagate = False

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload = {
                "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "level": record.levelname,
                "msg": record.getMessage(),
            }
            if hasattr(record, "meta"):
                try:
                    payload["meta"] = record.meta
                except Exception:
                    payload["meta"] = str(record.meta)
            return json.dumps(payload, ensure_ascii=True)

    class TextFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            meta = ""
            if hasattr(record, "meta"):
                meta = f" | {record.meta}"
            return f"[{ts}] {record.levelname:5s} {record.getMessage()}{meta}"

    # Console handler (human-friendly text)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(TextFormatter())
    logger.addHandler(sh)

    # Optional file handler (machine-friendly JSONL)
    if save_path:
        fh = logging.FileHandler(save_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(JsonFormatter())
        logger.addHandler(fh)

    return logger

class ChatServer:
    def __init__(self, host: str, port: int, logger: logging.Logger):
        self.host = host
        self.port = port
        self.log = logger
        self.clients: dict[asyncio.StreamWriter, str | None] = {}
        self.nick_to_writer: dict[str, asyncio.StreamWriter] = {}
        self.lock = asyncio.Lock()

    def ts(self) -> str:
        return datetime.now().strftime("%H:%M")

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addrs = ", ".join(str(s.getsockname()) for s in server.sockets)
        self.log.info("Listening", extra={"meta": {"bind": addrs}})
        async with server:
            await server.serve_forever()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info("peername")
        self.log.info("Connection open", extra={"meta": {"peer": str(peer)}})
        self.clients[writer] = None

        try:
            await self.send_line(writer, WELCOME)
            while True:
                raw = await reader.readline()
                if not raw:
                    await self.disconnect(writer, reason="client closed")
                    return
                line = raw.decode(errors="ignore").rstrip("\r\n")
                nick = self.clients.get(writer) or "(unnamed)"
                self.log.debug("Line received", extra={"meta": {"peer": str(peer), "nick": nick, "line": line}})

                if not line:
                    continue
                if line.startswith("/"):
                    await self.handle_command(writer, line)
                else:
                    await self.handle_chat(writer, line)
        except (asyncio.IncompleteReadError, ConnectionResetError) as e:
            self.log.warning("Transport error", extra={"meta": {"peer": str(peer), "error": str(e)}})
            await self.disconnect(writer, reason="transport error")
        except Exception as e:
            self.log.exception("Unexpected error")
            await self.disconnect(writer, reason="server error")

    async def handle_command(self, writer: asyncio.StreamWriter, line: str):
        parts = line.split(maxsplit=2)
        cmd = parts[0].lower()
        nick = self.clients.get(writer)

        self.log.info("Command", extra={"meta": {"cmd": cmd, "args": parts[1:] if len(parts) > 1 else [], "nick": nick}})

        if cmd == "/help":
            await self.send_line(writer, HELP)
            return

        if cmd == "/quit":
            await self.disconnect(writer, reason="quit")
            return

        if cmd == "/nick":
            if len(parts) < 2 or not parts[1].strip():
                await self.send_line(writer, "Usage: /nick <name>\n")
                return
            newnick = parts[1].strip()
            if " " in newnick:
                await self.send_line(writer, "Nickname cannot contain spaces.\n")
                return
            async with self.lock:
                if newnick.lower() in (n.lower() for n in self.nick_to_writer.keys()):
                    await self.send_line(writer, "Nickname already in use. Try another.\n")
                    return
                old = self.clients.get(writer)
                if old:
                    self.nick_to_writer.pop(old, None)
                self.clients[writer] = newnick
                self.nick_to_writer[newnick] = writer
            if old:
                self.log.info("Nick change", extra={"meta": {"old": old, "new": newnick}})
                await self.broadcast(f"* {old} is now known as {newnick}")
            else:
                self.log.info("Nick set", extra={"meta": {"new": newnick}})
                await self.send_line(writer, f"OK. You are now '{newnick}'.\n")
                await self.broadcast(f"* {newnick} joined the chat", exclude={writer})
            return

        if cmd == "/list":
            users = [n for n in self.nick_to_writer.keys()]
            users.sort(key=lambda x: x.lower())
            await self.send_line(writer, "Users ({}): {}\n".format(len(users), ", ".join(users)))
            return

        if cmd == "/msg":
            if len(parts) < 3:
                await self.send_line(writer, "Usage: /msg <user> <message>\n")
                return
            target, text = parts[1], parts[2]
            sender = self.clients.get(writer)
            if not sender:
                await self.send_line(writer, "Set your nickname first: /nick <name>\n")
                return
            async with self.lock:
                tw = self.nick_to_writer.get(target)
            if not tw:
                self.log.info("PM target not found", extra={"meta": {"from": sender, "to": target}})
                await self.send_line(writer, f"User '{target}' not found.\n")
                return
            await self.safe_send(tw, f"[{self.ts()}] [PM] <{sender}> {text}\n")
            await self.send_line(writer, f"[PM -> {target}] {text}\n")
            self.log.info("PM sent", extra={"meta": {"from": sender, "to": target, "len": len(text)}})
            return

        if cmd == "/me":
            if len(parts) < 2:
                await self.send_line(writer, "Usage: /me <action>\n")
                return
            sender = self.clients.get(writer)
            if not sender:
                await self.send_line(writer, "Set your nickname first: /nick <name>\n")
                return
            action = parts[1]
            await self.broadcast(f"* {sender} {action}")
            self.log.info("Emote", extra={"meta": {"nick": sender, "action": action}})
            return

        await self.send_line(writer, "Unknown command. Type /help\n")

    async def handle_chat(self, writer: asyncio.StreamWriter, text: str):
        sender = self.clients.get(writer)
        if not sender:
            await self.send_line(writer, "Set your nickname first: /nick <name>\n")
            return
        self.log.info("Public message", extra={"meta": {"from": sender, "len": len(text), "preview": text[:80]}})
        await self.broadcast(f"<{sender}> {text}")

    async def broadcast(self, text: str, exclude: set[asyncio.StreamWriter] | None = None):
        exclude = exclude or set()
        line = f"[{self.ts()}] {text}\n"
        dead: list[asyncio.StreamWriter] = []
        async with self.lock:
            for w in list(self.clients.keys()):
                if w in exclude:
                    continue
                try:
                    w.write(line.encode())
                    await w.drain()
                except Exception:
                    dead.append(w)
        for w in dead:
            await self.disconnect(w, reason="broken pipe")

    async def send_line(self, writer: asyncio.StreamWriter, text: str):
        try:
            writer.write(text.encode())
            await writer.drain()
        except Exception:
            await self.disconnect(writer, reason="send failed")

    async def safe_send(self, writer: asyncio.StreamWriter, text: str):
        try:
            writer.write(text.encode())
            await writer.drain()
        except Exception:
            pass

    async def disconnect(self, writer: asyncio.StreamWriter, reason: str = "bye"):
        name = self.clients.get(writer)
        peer = writer.get_extra_info("peername")
        async with self.lock:
            if writer in self.clients:
                self.clients.pop(writer, None)
            if name:
                self.nick_to_writer.pop(name, None)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        self.log.info("Connection closed", extra={"meta": {"peer": str(peer), "nick": name, "reason": reason}})
        if name:
            await self.broadcast(f"* {name} left ({reason})")

def main():
    ap = argparse.ArgumentParser(
        description="Async terminal chat server (single optional --save to record session)",
        add_help=True
    )
    ap.add_argument("--save", metavar="PATH", help="Save full session to PATH as JSON Lines (console output remains)")
    args = ap.parse_args()

    host = "0.0.0.0"
    port = 5555

    logger = setup_logger(args.save)
    srv = ChatServer(host, port, logger)
    try:
        asyncio.run(srv.start())
    except KeyboardInterrupt:
        logger.info("Server shutting down")

if __name__ == "__main__":
    main()


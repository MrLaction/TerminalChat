#!/usr/bin/env python3
import asyncio
import argparse
import sys

HELP = (
    "Type messages and press Enter to chat. Commands: \n"
    "/help, /nick <name>, /list, /msg <user> <text>, /me <action>, /quit\n"
)

async def stdin_reader(queue: asyncio.Queue):
    loop = asyncio.get_running_loop()
    # Read lines from stdin without blocking the event loop
    while True:
        line = await asyncio.to_thread(sys.stdin.readline)
        if line == '':
            await queue.put('/quit')
            return
        await queue.put(line.rstrip('\
'))

async def run_client(host: str, port: int, nick: str | None):
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except Exception as e:
        print(f"[ERR] Cannot connect to {host}:{port} -> {e}")
        return

    print(f"[INFO] Connected to {host}:{port}")

    # If we have a nickname, set it immediately
    if nick:
        writer.write(f"/nick {nick}\n".encode())
        await writer.drain()

    inbox = asyncio.create_task(server_to_stdout(reader))
    outq: asyncio.Queue[str] = asyncio.Queue()
    keyboard = asyncio.create_task(stdin_reader(outq))

    try:
        while True:
            line = await outq.get()
            if not line:
                continue
            if line.strip().lower() == '/help':
                print(HELP, end='')
                continue
            writer.write((line + "\n").encode())
            await writer.drain()
            if line.strip().lower() == '/quit':
                break
    except KeyboardInterrupt:
        pass
    finally:
        try:
            writer.write(b"/quit\n")
            await writer.drain()
        except Exception:
            pass
        writer.close()
        await writer.wait_closed()
        inbox.cancel()
        keyboard.cancel()
        print("[INFO] Disconnected")

async def server_to_stdout(reader: asyncio.StreamReader):
    try:
        while True:
            data = await reader.readline()
            if not data:
                print("[INFO] Server closed the connection")
                return
            sys.stdout.write(data.decode(errors='ignore'))
            sys.stdout.flush()
    except asyncio.CancelledError:
        return


def main():
    ap = argparse.ArgumentParser(description="Async terminal chat client")
    ap.add_argument("--host", default="127.0.0.1", help="Server IP/host (default 127.0.0.1)")
    ap.add_argument("--port", type=int, default=5555, help="Server TCP port (default 5555)")
    ap.add_argument("--nick", help="Nickname (you can also set later with /nick)")
    args = ap.parse_args()

    try:
        asyncio.run(run_client(args.host, args.port, args.nick))
    except KeyboardInterrupt:
        print("\n[INFO] Exiting")

if __name__ == "__main__":
    main()


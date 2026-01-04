import asyncio
import time
import signal
from collections import defaultdict

from src.http_parser import parse_http_request
from src.policy_engine import evaluate, evaluate_tls
from src.tls_parser import extract_sni
from src.observability import log_event, inc, snapshot

CONFIG = None
SHUTTING_DOWN = False

active_connections = 0
connections_per_ip = defaultdict(int)
lock = asyncio.Lock()


async def pipe(reader, writer):
    try:
        while True:
            data = await asyncio.wait_for(
                reader.read(CONFIG["buffer"]["size"]),
                timeout=CONFIG["timeouts"]["read"]
            )
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception:
        pass
    finally:
        writer.close()


async def handle_metrics(writer):
    metrics = snapshot()
    body = json = ""
    body = "\n".join(f"{k}: {v}" for k, v in metrics.items())

    response = (
        "HTTP/1.1 200 OK\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Content-Type: text/plain\r\n"
        "\r\n"
        f"{body}"
    )

    writer.write(response.encode())
    await writer.drain()
    writer.close()


async def handle_client(reader, writer):
    global active_connections

    if SHUTTING_DOWN:
        writer.close()
        return

    addr = writer.get_extra_info("peername")
    ip = addr[0]
    start = time.time()

    async with lock:
        if active_connections >= CONFIG["limits"]["max_connections"]:
            writer.write(b"HTTP/1.1 503 Service Unavailable\r\n\r\n")
            await writer.drain()
            writer.close()
            return

        if connections_per_ip[ip] >= CONFIG["limits"]["max_conn_per_ip"]:
            writer.close()
            return

        active_connections += 1
        connections_per_ip[ip] += 1

    inc("connections_total")
    log_event("connection_open", client=addr)

    try:
        data = b""
        start_hdr = time.time()

        while True:
            if time.time() - start_hdr > CONFIG["timeouts"]["header_read"]:
                raise TimeoutError("header_timeout")

            chunk = await reader.read(CONFIG["buffer"]["size"])
            if not chunk:
                return

            data += chunk
            if len(data) > CONFIG["limits"]["max_header_bytes"]:
                raise ValueError("header_too_large")

            if b"\r\n\r\n" in data:
                break

        # --- METRICS ENDPOINT ---
        if data.startswith(b"GET /__metrics"):
            await handle_metrics(writer)
            return

        info = parse_http_request(data)
        inc("requests_total")

        allowed, _ = evaluate(info, addr, CONFIG)
        if not allowed:
            inc("requests_blocked")
            writer.write(b"HTTP/1.1 403 Forbidden\r\n\r\n")
            await writer.drain()
            return

        if info["method"] == "CONNECT":
            inc("tls_connections")
            sreader, swriter = await asyncio.open_connection(info["host"], info["port"])

            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()

            tls_data = await reader.read(CONFIG["buffer"]["size"])
            sni = extract_sni(tls_data)

            allowed, _ = evaluate_tls(sni, CONFIG)
            if not allowed:
                inc("tls_blocked")
                writer.close()
                swriter.close()
                return

            swriter.write(tls_data)
            await swriter.drain()

            await asyncio.wait(
                [
                    asyncio.create_task(pipe(reader, swriter)),
                    asyncio.create_task(pipe(sreader, writer))
                ],
                return_when=asyncio.FIRST_COMPLETED
            )
            return

        sreader, swriter = await asyncio.open_connection(info["host"], info["port"])
        req = (
            f"{info['method']} {info['path']} {info['version']}\r\n"
            f"Host: {info['host']}\r\nConnection: close\r\n\r\n"
        )
        swriter.write(req.encode())
        await swriter.drain()

        while True:
            resp = await sreader.read(CONFIG["buffer"]["size"])
            if not resp:
                break
            writer.write(resp)
            await writer.drain()

    finally:
        async with lock:
            active_connections -= 1
            connections_per_ip[ip] -= 1

        inc("connections_closed")
        log_event("connection_closed", duration_ms=int((time.time() - start) * 1000))
        writer.close()
        await writer.wait_closed()


async def start_proxy(config):
    global CONFIG, SHUTTING_DOWN
    CONFIG = config

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def shutdown():
        global SHUTTING_DOWN
        SHUTTING_DOWN = True
        log_event("shutdown", level="warn")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    server = await asyncio.start_server(
        handle_client,
        config["server"]["host"],
        config["server"]["port"]
    )

    log_event("proxy_started", **config["server"])

    async with server:
        await stop.wait()
        server.close()
        await server.wait_closed()
        log_event("proxy_stopped", level="warn")

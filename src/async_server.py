import asyncio

HOST = "127.0.0.1"
PORT = 8888

async def handle_client(reader: asyncio.StreamReader,
                        writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    print(f"[+] Connected {addr}")

    try:
        data = await reader.read(1024)
        print(f"[{addr}] Received:", data)

        writer.write(b"Hello from async server")
        await writer.drain()

    except Exception as e:
        print("[!] Error:", e)

    finally:
        writer.close()
        await writer.wait_closed()
        print(f"[-] Closed {addr}")

async def main():
    server = await asyncio.start_server(
        handle_client, HOST, PORT
    )

    print(f"[+] Async server listening on {HOST}:{PORT}")

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())

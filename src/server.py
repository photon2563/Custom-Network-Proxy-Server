import socket
import threading
import select
from src.http_parser import parse_http_request

HOST = "127.0.0.1"
PORT = 8888
BUFFER_SIZE = 4096

def tunnel(client_socket, server_socket):
    """
    Bidirectional TCP tunnel for HTTPS.
    Forwards bytes blindly in both directions.
    """
    sockets = [client_socket, server_socket]

    while True:
        readable, _, _ = select.select(sockets, [], [])

        for sock in readable:
            data = sock.recv(4096)
            if not data:
                return

            if sock is client_socket:
                server_socket.sendall(data)
            else:
                client_socket.sendall(data)


def handle_client(client_socket, client_address):
    print(f"[+] New connection {client_address}")

    try:
        # 1. Read initial request
        request = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                return
            request += chunk
            if b"\r\n\r\n" in request:
                break

        # 2. Parse request
        info = parse_http_request(request)
        method = info["method"]
        host = info["host"]
        port = info["port"]
        path = info["path"]
        version = info["version"]

        print(f"[>] {method} {host}:{port}")

        # ===================== HTTPS =====================
        if method == "CONNECT":
            # Connect to target server
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.connect((host, port))

            # Tell client tunnel is ready
            client_socket.sendall(
                b"HTTP/1.1 200 Connection Established\r\n\r\n"
            )

            # Start raw tunnel
            tunnel(client_socket, server_socket)

            server_socket.close()
            return

        # ===================== HTTP ======================
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.connect((host, port))

        # Rewrite HTTP request
        new_request = (
            f"{method} {path} {version}\r\n"
            f"Host: {host}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )

        server_socket.sendall(new_request.encode())

        # Relay response
        while True:
            response = server_socket.recv(4096)
            if not response:
                break
            client_socket.sendall(response)

        server_socket.close()

    except Exception as e:
        print("[!] Error:", e)

    finally:
        client_socket.close()
        print(f"[-] Closed {client_address}")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", 8888))
    server_socket.listen()

    print("[+] Proxy listening on 127.0.0.1:8888")

    while True:
        client_socket, client_address = server_socket.accept()
        threading.Thread(
            target=handle_client,
            args=(client_socket, client_address),
            daemon=True
        ).start()


if __name__ == "__main__":
    start_server()

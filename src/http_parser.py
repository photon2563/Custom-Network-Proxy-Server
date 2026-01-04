from urllib.parse import urlparse

def parse_http_request(data: bytes):
    line = data.decode(errors="ignore").split("\r\n")[0]
    method, target, version = line.split()

    if method == "CONNECT":
        host, port = target.split(":")
        return {
            "method": method,
            "host": host,
            "port": int(port),
            "path": None,
            "version": version
        }

    parsed = urlparse(target)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    return {
        "method": method,
        "host": parsed.hostname,
        "port": parsed.port or 80,
        "path": path,
        "version": version
    }

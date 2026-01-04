def extract_sni(data: bytes):
    try:
        if data[0] != 0x16:
            return None
        pos = 5
        if data[pos] != 0x01:
            return None

        pos += 4 + 2 + 32
        pos += 1 + data[pos]

        cs_len = int.from_bytes(data[pos:pos+2], "big")
        pos += 2 + cs_len

        pos += 1 + data[pos]

        ext_len = int.from_bytes(data[pos:pos+2], "big")
        pos += 2
        end = pos + ext_len

        while pos + 4 <= end:
            etype = int.from_bytes(data[pos:pos+2], "big")
            size = int.from_bytes(data[pos+2:pos+4], "big")
            pos += 4

            if etype == 0:
                pos += 2 + 1
                name_len = int.from_bytes(data[pos:pos+2], "big")
                pos += 2
                return data[pos:pos+name_len].decode()

            pos += size
    except Exception:
        return None

def evaluate(info, client_addr, config):
    if info["method"] not in config["policy"]["allowed_methods"]:
        return False, "method_not_allowed"

    for d in config["policy"]["blocked_domains"]:
        if info["host"].endswith(d):
            return False, "domain_blocked"

    return True, "allowed"

def evaluate_tls(sni, config):
    if not sni:
        return True, "no_sni"

    for d in config["tls"]["blocked_sni"]:
        if sni.endswith(d):
            return False, "tls_blocked"

    return True, "tls_allowed"

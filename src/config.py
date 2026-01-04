import yaml # type: ignore
import copy

def deep_merge(base, override):
    result = copy.deepcopy(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

def load_config(default_path, override_path=None):
    with open(default_path) as f:
        base = yaml.safe_load(f)

    if override_path:
        try:
            with open(override_path) as f:
                override = yaml.safe_load(f)
            return deep_merge(base, override)
        except FileNotFoundError:
            pass

    return base

import time
import json
from collections import defaultdict

_metrics = defaultdict(int)
START_TIME = time.time()

LOG_LEVEL = "info"
LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}


def set_log_level(level):
    global LOG_LEVEL
    LOG_LEVEL = level


def inc(name, value=1):
    _metrics[name] += value


def snapshot():
    return {
        **_metrics,
        "uptime_seconds": int(time.time() - START_TIME)
    }


def log_event(event, level="info", **fields):
    if LEVELS[level] < LEVELS[LOG_LEVEL]:
        return
    print(json.dumps({
        "ts": time.time(),
        "level": level,
        "event": event,
        **fields
    }))

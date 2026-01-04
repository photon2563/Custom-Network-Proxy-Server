import argparse
import asyncio

from src.config import load_config
from src.async_proxy import start_proxy
from src.observability import set_log_level

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config/default.yaml")
    p.add_argument("--override", default=None)
    p.add_argument("--log-level", default="info", choices=["debug","info","warn","error"])
    args = p.parse_args()

    set_log_level(args.log_level)
    config = load_config(args.config, args.override)

    asyncio.run(start_proxy(config))

if __name__ == "__main__":
    main()

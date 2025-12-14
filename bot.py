import time
import os
import requests


WEB_HOST = os.getenv("WEB_HOST", "web")
WEB_PORT = int(os.getenv("WEB_PORT", "8000"))
INTERVAL = int(os.getenv("BOT_INTERVAL", "5"))  # секунды между проверками


def main():
    url = f"http://{WEB_HOST}:{WEB_PORT}/health"
    print(f"[bot] Starting healthcheck loop for {url}, interval={INTERVAL}s", flush=True)

    while True:
        try:
            resp = requests.get(url, timeout=2)
            body = resp.text.strip()
            print(f"[bot] {resp.status_code} {body}", flush=True)
        except Exception as e:
            print(f"[bot] ERROR: {e}", flush=True)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()

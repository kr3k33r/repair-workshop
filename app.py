import argparse
from pathlib import Path
from engine import Workshop, DEVICES, ISSUES, STATUSES, quote
from local_server import serve

ROOT = Path(__file__).resolve().parent
workshop = None


def get_api(path, query):
    if path == "/api/config":
        return {"devices": DEVICES, "issues": ISSUES, "statuses": STATUSES}
    if path == "/api/requests":
        return {"requests": workshop.listing(), "statuses": STATUSES}


def post_api(path, payload):
    if path == "/api/quote":
        return quote(payload.get("device"), payload.get("issue"))
    if path == "/api/requests":
        return workshop.submit(payload)
    if path == "/api/status":
        return workshop.set_status(payload.get("id"), payload.get("status"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--database", default=str(ROOT / "runtime" / "requests.sqlite3"))
    args = parser.parse_args()
    workshop = Workshop(args.database)
    serve(ROOT / "web", get_api, post_api, args.port)

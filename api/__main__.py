"""Start the dashboard server:  uv run python -m api  [--port 8000] [--reload]"""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the World GDP Dashboard server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="restart when Python files change")
    args = parser.parse_args()
    print(f"Dashboard: http://{args.host}:{args.port}    API docs: http://{args.host}:{args.port}/docs")
    uvicorn.run("api.main:app", host=args.host, port=args.port, reload=args.reload,
                reload_dirs=["api"] if args.reload else None)


if __name__ == "__main__":
    main()

import uvicorn
from pyharness.webui.server import create_app


def main():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
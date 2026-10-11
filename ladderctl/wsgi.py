from app import create_app

app = create_app()

if __name__ == "__main__":
    import os

    port = int(os.environ.get("LADDERCTL_PORT", 8001))
    app.run(host="0.0.0.0", port=port, debug=True)

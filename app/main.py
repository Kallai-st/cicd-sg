from pathlib import Path

from flask import Flask, jsonify


def create_app():
    app = Flask(__name__)

    #demo rollback
    Path("/var/tmp/startup.marker").write_text("started")

    @app.get("/")
    def index():
        return jsonify(message="Hello a CI/CD demo alkalmazásból!")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

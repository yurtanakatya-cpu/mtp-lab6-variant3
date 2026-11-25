"""Приложение для лабораторной по веб-программированию."""

from flask import Flask


def create_app() -> Flask:
    """Создать приложение Flask."""
    app = Flask(__name__)

    @app.get("/")
    def about():
        return app.send_static_file("about.html")

    return app

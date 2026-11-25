"""Приложение для лабораторной по веб-программированию."""

from flask import Flask, render_template


def create_app() -> Flask:
    """Создать приложение Flask."""
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/about")
    def about():
        return app.send_static_file("about.html")

    return app

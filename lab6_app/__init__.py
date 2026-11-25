"""Приложение для лабораторной по веб-программированию."""

from flask import Flask, abort, render_template, request

from .tasks import LEVELS, TASKS


def create_app() -> Flask:
    """Создать приложение Flask."""
    app = Flask(__name__)

    @app.get("/")
    def index():
        """Отфильтровать список заданий и передать его в шаблон."""
        level = request.args.get("level", "")
        if level and level not in LEVELS:
            abort(400, description="Неизвестный уровень сложности.")
        tasks = [task for task in TASKS if not level or task[0] == level]
        return render_template(
            "index.html", tasks=tasks, levels=LEVELS, selected=level
        )

    @app.get("/about")
    def about():
        """Вернуть готовый HTML без обработки Jinja."""
        return app.send_static_file("about.html")

    return app

"""Приложение для лабораторной по веб-программированию."""

from datetime import timedelta
from json import load
from os import environ
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from .auth import auth, csrf_token, signed_in

from .tasks import LEVELS, TASKS


INSTANCE_DIR = Path(__file__).resolve().parents[1] / "instance"


def create_app(test_config: dict | None = None) -> Flask:
    """Загрузить настройки и зарегистрировать маршруты."""
    production = environ.get("LAB6_ENV") == "production"
    app = Flask(__name__, instance_path=str(INSTANCE_DIR))
    app.config.update(
        LAB6_USERNAME="",
        LAB6_PASSWORD_HASH="",
        LAB6_SECRET_KEY="",
        SESSION_COOKIE_NAME="lab6_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=production,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_REFRESH_EACH_REQUEST=False,
        PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
        MAX_CONTENT_LENGTH=8 * 1024,
    )
    if not production:
        app.config.from_file("config.json", load=load, silent=True)
    keys = ("LAB6_USERNAME", "LAB6_PASSWORD_HASH", "LAB6_SECRET_KEY")
    for key in keys:
        if key in environ:
            app.config[key] = environ[key]
    if test_config is not None:
        app.config.update(test_config)

    if production or any(app.config[key] for key in keys):
        if not all(app.config[key] for key in keys):
            raise RuntimeError("Укажите все три переменные LAB6 для входа.")
        if len(app.config["LAB6_SECRET_KEY"]) < 32:
            raise RuntimeError("LAB6_SECRET_KEY должен быть не короче 32 знаков.")
        app.secret_key = app.config["LAB6_SECRET_KEY"]

    if production:
        # Heroku передаёт исходную схему через один доверенный прокси.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

        @app.before_request
        def require_https():
            if request.is_secure or request.endpoint == "health":
                return None
            if request.method not in {"GET", "HEAD"}:
                abort(400, description="Для отправки формы нужен HTTPS.")
            return redirect(request.url.replace("http:", "https:", 1), 308)

    app.register_blueprint(auth)
    app.add_template_global(csrf_token)
    app.add_template_global(signed_in)

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

    @app.get("/healthz")
    def health():
        """Вернуть простой ответ для проверки работы процесса."""
        return {"status": "ok"}

    @app.after_request
    def secure_headers(response):
        """Ограничить источники ресурсов и встраивание страницы."""
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; form-action 'self'; base-uri 'none'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        if production and request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    return app

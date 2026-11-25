"""Вход, закрытая страница и выход из сессии."""

from hmac import compare_digest
from secrets import token_urlsafe

from flask import (
    Blueprint, abort, current_app, redirect, render_template, request,
    session, url_for,
)
from werkzeug.security import check_password_hash


auth = Blueprint("auth", __name__)


def csrf_token() -> str:
    """Создать токен для формы и сохранить его в сессии."""
    if "csrf" not in session:
        session["csrf"] = token_urlsafe(32)
    return session["csrf"]


def validate_csrf() -> None:
    """Проверить принадлежность POST-запроса текущей сессии."""
    expected = session.get("csrf")
    received = request.form.get("csrf_token", "")
    if not expected or not compare_digest(
        received.encode("utf-8"), expected.encode("utf-8")
    ):
        abort(400, description="Обновите страницу и повторите действие.")


def signed_in() -> bool:
    """Проверить, что сессия принадлежит настроенному пользователю."""
    user = session.get("user")
    return bool(user and user == current_app.config["LAB6_USERNAME"])


@auth.after_request
def disable_cache(response):
    """Кэш браузера не должен сохранять формы и закрытую страницу."""
    response.headers["Cache-Control"] = "no-store"
    return response


@auth.route("/login", methods=["GET", "POST"])
def login():
    """Проверить имя и хеш пароля, затем открыть личный кабинет."""
    config = current_app.config
    if not config["LAB6_PASSWORD_HASH"]:
        return render_template(
            "login.html", unavailable=True, error=None
        ), 503
    if signed_in() and request.method == "GET":
        return redirect(url_for("auth.account"))
    if request.method == "GET":
        return render_template("login.html", unavailable=False, error=None)

    validate_csrf()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if 1 <= len(username) <= 64 and 1 <= len(password) <= 128:
        password_ok = check_password_hash(config["LAB6_PASSWORD_HASH"], password)
        username_ok = compare_digest(
            username.encode("utf-8"), config["LAB6_USERNAME"].encode("utf-8")
        )
        if username_ok and password_ok:
            session.clear()
            session["user"] = config["LAB6_USERNAME"]
            session.permanent = True
            return redirect(url_for("auth.account"), 303)
    return render_template(
        "login.html", unavailable=False, error="Неверное имя или пароль."
    ), 401


@auth.get("/account")
def account():
    """Показать кабинет только после входа."""
    if not signed_in():
        return redirect(url_for("auth.login"))
    return render_template("account.html", username=session["user"])


@auth.post("/logout")
def logout():
    """Завершить сеанс из формы в кабинете."""
    validate_csrf()
    session.clear()
    return redirect(url_for("index"), 303)

"""Проверки HTTP-ответов, форм и закрытого кабинета."""

import re
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from lab6_app import create_app


PASSWORD = "test-password-for-lab6"
CONFIG = {
    "TESTING": True,
    "LAB6_USERNAME": "Студент",
    "LAB6_PASSWORD_HASH": generate_password_hash(PASSWORD),
    "LAB6_SECRET_KEY": "a" * 64,
}


def form_token(response) -> str:
    """Извлечь CSRF-токен из реально отрисованной формы."""
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    if match is None:
        raise AssertionError("В HTML нет токена формы.")
    return match.group(1)


class PageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = create_app(CONFIG).test_client()

    def test_about_serves_static_html_and_css(self) -> None:
        with self.client.get("/about") as page:
            self.assertEqual(page.status_code, 200)
            self.assertIn('/static/site.css', page.get_data(as_text=True))
        with self.client.get("/static/site.css") as stylesheet:
            self.assertEqual(stylesheet.status_code, 200)
            self.assertEqual(stylesheet.mimetype, "text/css")

    def test_index_renders_all_rows_and_bootstrap(self) -> None:
        page = self.client.get("/").get_data(as_text=True)
        self.assertIn("bootstrap@5.3.9/dist/css/bootstrap.min.css", page)
        self.assertIn('class="table table-striped', page)
        self.assertEqual(page.count("<tr>"), 6)

    def test_filter_selects_rows_and_rejects_unknown_level(self) -> None:
        page = self.client.get("/?level=medium").get_data(as_text=True)
        self.assertIn("Статическая страница с CSS", page)
        self.assertNotIn("Деплой на Heroku", page)
        self.assertEqual(page.count("<tr>"), 4)
        page = self.client.get("/?level=advanced").get_data(as_text=True)
        self.assertIn("Деплой на Heroku", page)
        self.assertNotIn("Статическая страница с CSS", page)
        self.assertEqual(page.count("<tr>"), 3)
        self.assertEqual(self.client.get("/?level=unknown").status_code, 400)

    def test_health_endpoint(self) -> None:
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})


class AuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = create_app(CONFIG).test_client()

    def login(self, password: str = PASSWORD, username: str = "Студент"):
        token = form_token(self.client.get("/login"))
        return self.client.post(
            "/login",
            data={"username": username, "password": password,
                  "csrf_token": token},
        )

    def test_account_redirects_when_signed_out(self) -> None:
        response = self.client.get("/account")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, "/login")
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_wrong_credentials_preserve_closed_account(self) -> None:
        for username, password in (
            ("Студент", "неверный-пароль"), ("Гость", PASSWORD)
        ):
            with self.subTest(username=username):
                response = self.login(password, username)
                self.assertEqual(response.status_code, 401)
                self.assertIn("Неверное имя", response.get_data(as_text=True))
                self.assertEqual(self.client.get("/account").status_code, 302)

    def test_login_and_logout(self) -> None:
        response = self.login()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, "/account")
        self.assertIn("HttpOnly", response.headers["Set-Cookie"])
        self.assertIn("SameSite=Lax", response.headers["Set-Cookie"])
        account = self.client.get("/account")
        self.assertEqual(account.status_code, 200)
        self.assertIn("Студент", account.get_data(as_text=True))
        self.assertNotIn(PASSWORD, account.get_data(as_text=True))
        response = self.client.post(
            "/logout", data={"csrf_token": form_token(account)}
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(self.client.get("/account").location, "/login")

    def test_post_requires_csrf_and_logout_rejects_get(self) -> None:
        self.assertEqual(self.client.post("/login").status_code, 400)
        self.login()
        self.assertEqual(self.client.get("/logout").status_code, 405)
        response = self.client.post("/logout", data={"csrf_token": "wrong"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.get("/account").status_code, 200)

    def test_login_unavailable_without_credentials(self) -> None:
        config = dict.fromkeys(
            ("LAB6_USERNAME", "LAB6_PASSWORD_HASH", "LAB6_SECRET_KEY"), ""
        )
        client = create_app(config).test_client()
        self.assertEqual(client.get("/").status_code, 200)
        self.assertEqual(client.get("/login").status_code, 503)

    def test_production_requires_credentials_and_uses_https_cookie(self) -> None:
        with patch.dict("os.environ", {"LAB6_ENV": "production"}):
            config = dict.fromkeys(
                ("LAB6_USERNAME", "LAB6_PASSWORD_HASH", "LAB6_SECRET_KEY"), ""
            )
            with self.assertRaisesRegex(RuntimeError, "три переменные"):
                create_app(config)
            client = create_app(CONFIG).test_client()
            response = client.get(
                "/login", headers={"X-Forwarded-Proto": "https"}
            )
            self.assertIn("Secure", response.headers["Set-Cookie"])
            response = client.get("/login")
            self.assertEqual(response.status_code, 308)
            self.assertEqual(response.location, "https://localhost/login")

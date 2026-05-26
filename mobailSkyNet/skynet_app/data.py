from __future__ import annotations

import hashlib
import json
import random
import sqlite3
from csv import DictWriter
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
import re
import smtplib
from urllib import request as urlrequest
from urllib.error import URLError

from skynet_app.theme import PRIORITY_LABELS, ROLE_LABELS, STATUS_LABELS


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def check_password_policy(password):
    if len(password) < 8:
        return False, "Пароль должен быть не менее 8 символов."
    if not re.search(r"\d", password):
        return False, "Пароль должен содержать цифру."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;/]', password):
        return False, "Пароль должен содержать спецсимвол."
    return True, None


class LocalRepository:
    def __init__(self, db_path, config=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.current_user_id = None
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    login TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role_id INTEGER NOT NULL,
                    organization TEXT DEFAULT '',
                    avatar_path TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(role_id) REFERENCES roles(id)
                );
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS statuses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    author_id INTEGER NOT NULL,
                    assignee_id INTEGER,
                    category_id INTEGER NOT NULL,
                    status_id INTEGER NOT NULL,
                    priority TEXT NOT NULL,
                    organization TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(author_id) REFERENCES users(id),
                    FOREIGN KEY(assignee_id) REFERENCES users(id),
                    FOREIGN KEY(category_id) REFERENCES categories(id),
                    FOREIGN KEY(status_id) REFERENCES statuses(id)
                );
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    author_id INTEGER,
                    author_name TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(ticket_id) REFERENCES tickets(id),
                    FOREIGN KEY(author_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS knowledge_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(category_id) REFERENCES categories(id),
                    FOREIGN KEY(created_by) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id INTEGER,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER,
                    details TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(actor_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    path TEXT DEFAULT '',
                    uploaded_by INTEGER,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(ticket_id) REFERENCES tickets(id),
                    FOREIGN KEY(uploaded_by) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS password_resets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    code TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    used INTEGER DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
                """
            )
            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_tickets_author ON tickets(author_id);
                CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status_id);
                CREATE INDEX IF NOT EXISTS idx_tickets_created ON tickets(created_at);
                CREATE INDEX IF NOT EXISTS idx_logs_entity ON logs(entity_type, entity_id);
                """
            )
            reset_columns = {row["name"] for row in conn.execute("PRAGMA table_info(password_resets)")}
            if "token_hash" not in reset_columns:
                conn.execute("ALTER TABLE password_resets ADD COLUMN token_hash TEXT DEFAULT ''")
            if "expires_at" not in reset_columns:
                conn.execute("ALTER TABLE password_resets ADD COLUMN expires_at TEXT DEFAULT ''")
            self._seed(conn)
            self._ensure_extra_knowledge(conn)

    def _seed(self, conn):
        role_count = conn.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
        if role_count:
            return

        roles = [
            ("client", "Клиент"),
            ("operator", "Оператор"),
            ("admin", "Администратор"),
        ]
        conn.executemany("INSERT INTO roles(code, name) VALUES (?, ?)", roles)

        statuses = [(code, STATUS_LABELS[code]) for code in ("new", "in_progress", "resolved", "closed")]
        conn.executemany("INSERT INTO statuses(code, name) VALUES (?, ?)", statuses)

        categories = [
            ("internet", "Проблемы с интернетом"),
            ("router", "Настройка роутера"),
            ("cabinet", "Личный кабинет"),
            ("billing", "Оплата и тарифы"),
        ]
        conn.executemany("INSERT INTO categories(code, name) VALUES (?, ?)", categories)

        created_at = now_str()
        users = [
            ("admin", "admin@skynet.local", "Алексей Волков", hash_password("admin123"), "admin", "Офис SkyNet"),
            ("operator", "operator@skynet.local", "Елена Смирнова", hash_password("operator123"), "operator", "Офис SkyNet"),
            ("ivan.petrov", "ivan.petrov@example.com", "Иван Петров", hash_password("client123"), "client", "Домашний интернет"),
            ("marina.orlova", "marina.orlova@example.com", "Марина Орлова", hash_password("client123"), "client", "Тариф Базовый"),
        ]
        for login, email, full_name, password_hash, role_code, organization in users:
            role_id = conn.execute("SELECT id FROM roles WHERE code = ?", (role_code,)).fetchone()[0]
            conn.execute(
                """
                INSERT INTO users(login, email, full_name, password_hash, role_id, organization, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (login, email, full_name, password_hash, role_id, organization, created_at),
            )

        category_map = {row["code"]: row["id"] for row in conn.execute("SELECT id, code FROM categories")}
        status_map = {row["code"]: row["id"] for row in conn.execute("SELECT id, code FROM statuses")}
        user_map = {row["login"]: row["id"] for row in conn.execute("SELECT id, login FROM users")}

        tickets = [
            (
                "Пропадает интернет вечером",
                "После 20:00 соединение часто обрывается на 1-2 минуты.",
                user_map["ivan.petrov"],
                user_map["operator"],
                category_map["internet"],
                status_map["in_progress"],
                "high",
                "Домашний интернет",
            ),
            (
                "Не входит в личный кабинет",
                "При входе появляется сообщение о неверном пароле.",
                user_map["ivan.petrov"],
                user_map["operator"],
                category_map["cabinet"],
                status_map["resolved"],
                "medium",
                "Личный кабинет",
            ),
            (
                "Требуется проверить оплату",
                "Деньги списались, но тариф не продлился.",
                user_map["marina.orlova"],
                None,
                category_map["billing"],
                status_map["new"],
                "medium",
                "Оплата услуг",
            ),
        ]
        for title, description, author_id, assignee_id, category_id, status_id, priority, organization in tickets:
            created = now_str()
            cursor = conn.execute(
                """
                INSERT INTO tickets(title, description, author_id, assignee_id, category_id, status_id, priority, organization, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title, description, author_id, assignee_id, category_id, status_id, priority, organization, created, created),
            )
            ticket_id = cursor.lastrowid
            if "Пропадает интернет" in title:
                conn.execute(
                    """
                    INSERT INTO comments(ticket_id, author_id, author_name, text, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (ticket_id, author_id, "Иван Петров", "Сделал скриншот теста скорости.", created),
                )
                conn.execute(
                    """
                    INSERT INTO comments(ticket_id, author_id, author_name, text, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (ticket_id, user_map["operator"], "Елена Смирнова", "Проверяем линию, ответим в течение дня.", created),
                )

        articles = [
            (
                category_map["internet"],
                "Что делать, если интернет не работает",
                "1. Перезагрузите роутер.\n\n2. Проверьте кабель.\n\n3. Убедитесь, что тариф активен.\n\n4. Если проблема остаётся, создайте заявку в приложении.",
            ),
            (
                category_map["router"],
                "Как изменить пароль Wi-Fi",
                "Откройте настройки роутера, найдите раздел беспроводной сети и обновите пароль. После сохранения переподключите устройства.",
            ),
            (
                category_map["cabinet"],
                "Не получается войти в личный кабинет",
                "Проверьте логин и пароль. Если доступ потерян, откройте раздел восстановления и создайте новый пароль.",
            ),
            (
                category_map["billing"],
                "Где посмотреть историю платежей",
                "Откройте профиль клиента и проверьте историю платежей. При спорном списании создайте заявку с подробностями.",
            ),
        ]
        for category_id, title, content in articles:
            conn.execute(
                """
                INSERT INTO knowledge_articles(category_id, title, content, created_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (category_id, title, content, user_map["admin"], created_at),
            )

        conn.execute(
            "INSERT INTO logs(actor_id, action, entity_type, entity_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_map["admin"], "seed", "system", None, "База приложения инициализирована демо-данными.", created_at),
        )
        conn.commit()

    def _ensure_extra_knowledge(self, conn):
        """Досеивание статей, даже если база уже была создана ранее."""
        existing = conn.execute("SELECT COUNT(*) FROM knowledge_articles").fetchone()[0]
        if existing >= 14:
            return

        category_map = {row["code"]: row["id"] for row in conn.execute("SELECT id, code FROM categories")}
        admin_id = conn.execute("SELECT id FROM users WHERE login = 'admin'").fetchone()
        admin_id = admin_id[0] if admin_id else 1

        extra = [
            ("internet", "Интернет работает медленно: быстрый чек‑лист", "1. Проверьте скорость по кабелю.\n\n2. Перезагрузите роутер.\n\n3. Проверьте нагрузку (торренты/обновления).\n\n4. Если проблема вечером — укажите время и приложите замеры."),
            ("internet", "Частые обрывы соединения", "Причины: слабый сигнал, плохой кабель, перегрев роутера.\n\nРешение: поменять кабель, переставить роутер, проверить питание, сделать фото индикации и создать заявку."),
            ("router", "Не видна Wi‑Fi сеть", "Проверьте, включён ли Wi‑Fi на роутере, перезагрузите устройство.\n\nЕсли сеть скрыта — включите SSID broadcast в настройках."),
            ("router", "Как сменить канал Wi‑Fi", "Если много соседних сетей, смените канал 1/6/11 (2.4GHz) или используйте 5GHz.\n\nПосле изменения сохраните настройки и переподключитесь."),
            ("cabinet", "Ошибка «неверный пароль»", "Используйте восстановление пароля через email.\n\nПароль: минимум 8 символов, цифра и спецсимвол."),
            ("cabinet", "Не приходит код восстановления", "Проверьте папку «Спам» и корректность email.\n\nВ офлайн‑версии код может отображаться прямо в приложении, если SMTP не настроен."),
            ("billing", "Платёж прошёл, но тариф не продлён", "Сохраните чек/скрин операции.\n\nСоздайте заявку и укажите сумму, дату и способ оплаты."),
            ("billing", "Как узнать текущий тариф", "Откройте профиль и проверьте поле «Организация/тариф».\n\nЕсли данных нет — укажите их в профиле или в заявке."),
        ]

        for category_code, title, content in extra:
            if conn.execute("SELECT 1 FROM knowledge_articles WHERE title = ?", (title,)).fetchone():
                continue
            category_id = category_map.get(category_code)
            if not category_id:
                continue
            conn.execute(
                """
                INSERT INTO knowledge_articles(category_id, title, content, created_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (category_id, title, content, admin_id, now_str()),
            )
        conn.commit()

    def _user_from_row(self, row):
        if not row:
            return self._guest_user()
        role_code = row["role_code"]
        return {
            "id": row["id"],
            "login": row["login"],
            "email": row["email"],
            "full_name": row["full_name"],
            "organization": row["organization"],
            "avatar_path": row["avatar_path"],
            "role_code": role_code,
            "role_name": row["role_name"],
            "is_client": role_code == "client",
            "is_operator": role_code in ("operator", "admin"),
            "is_admin": role_code == "admin",
            "is_authenticated": True,
        }

    def _guest_user(self):
        return {
            "id": None,
            "login": "",
            "email": "",
            "full_name": "Гость",
            "organization": "",
            "avatar_path": "",
            "role_code": "guest",
            "role_name": ROLE_LABELS["guest"],
            "is_client": False,
            "is_operator": False,
            "is_admin": False,
            "is_authenticated": False,
        }

    def _current_db_user(self, conn):
        if not self.current_user_id:
            return None
        return conn.execute(
            """
            SELECT users.*, roles.code AS role_code, roles.name AS role_name
            FROM users
            JOIN roles ON roles.id = users.role_id
            WHERE users.id = ?
            """,
            (self.current_user_id,),
        ).fetchone()

    def get_current_user(self):
        with self._connect() as conn:
            return self._user_from_row(self._current_db_user(conn))

    def logout(self):
        self.current_user_id = None

    def _log(self, conn, action, entity_type, entity_id=None, details=""):
        conn.execute(
            """
            INSERT INTO logs(actor_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (self.current_user_id, action, entity_type, entity_id, details, now_str()),
        )

    def login(self, login, password):
        with self._connect() as conn:
            user = conn.execute(
                """
                SELECT users.*, roles.code AS role_code, roles.name AS role_name
                FROM users
                JOIN roles ON roles.id = users.role_id
                WHERE users.login = ? OR users.email = ?
                """,
                (login.strip(), login.strip()),
            ).fetchone()
            if not user or user["password_hash"] != hash_password(password):
                raise ValueError("Неверный логин или пароль.")
            self.current_user_id = user["id"]
            self._log(conn, "login", "user", user["id"], "Пользователь выполнил вход в приложение.")
            conn.commit()
            return self._user_from_row(user)

    def register_user(self, login, email, full_name, password, organization=""):
        login = login.strip()
        email = email.strip().lower()
        full_name = full_name.strip()
        organization = organization.strip()
        if not login or not email or not full_name or not password:
            raise ValueError("Заполните логин, email, ФИО и пароль.")
        ok, error = check_password_policy(password)
        if not ok:
            raise ValueError(error)
        with self._connect() as conn:
            duplicate = conn.execute(
                "SELECT id FROM users WHERE login = ? OR email = ?",
                (login, email),
            ).fetchone()
            if duplicate:
                raise ValueError("Пользователь с таким логином или email уже существует.")
            role_id = conn.execute("SELECT id FROM roles WHERE code = 'client'").fetchone()[0]
            cursor = conn.execute(
                """
                INSERT INTO users(login, email, full_name, password_hash, role_id, organization, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (login, email, full_name, hash_password(password), role_id, organization, now_str()),
            )
            self.current_user_id = cursor.lastrowid
            self._log(conn, "register", "user", cursor.lastrowid, "Создан новый локальный клиент.")
            conn.commit()
            return self.get_current_user()

    def request_password_reset(self, login_or_email):
        login_or_email = login_or_email.strip().lower()
        with self._connect() as conn:
            user = conn.execute(
                "SELECT id, email FROM users WHERE lower(login) = ? OR lower(email) = ?",
                (login_or_email, login_or_email),
            ).fetchone()
            if not user:
                raise ValueError("Пользователь не найден.")
            code = str(random.randint(100000, 999999)).zfill(6)
            expires_at = datetime.now() + timedelta(minutes=getattr(self.config, "passwordResetExpireMinutes", 60))
            expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M")
            conn.execute("UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0", (user["id"],))
            conn.execute(
                """
                INSERT INTO password_resets(user_id, code, token_hash, created_at, expires_at, used)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (user["id"], "", hash_password(code), now_str(), expires_at_str),
            )
            sent_to_email = False
            if self.config:
                try:
                    self._send_reset_email(user["email"], code)
                    sent_to_email = True
                except Exception:
                    sent_to_email = False
            details = "Код восстановления отправлен на email." if sent_to_email else "Код восстановления создан локально."
            self._log(conn, "request_reset", "user", user["id"], details)
            conn.commit()
            return {
                "email": user["email"],
                "code": code,
                "sent_to_email": sent_to_email,
                "expires_at": expires_at_str,
                "expires_minutes": getattr(self.config, "passwordResetExpireMinutes", 60),
            }

    def reset_password(self, email, code, new_password, confirm_password):
        email = email.strip().lower()
        code = code.strip()
        with self._connect() as conn:
            if not email or not code:
                raise ValueError("Укажите email и код из письма.")
            user = conn.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone()
            if not user:
                raise ValueError("Неверный email или код.")
            if new_password != confirm_password:
                raise ValueError("Пароли не совпадают.")
            ok, error = check_password_policy(new_password)
            if not ok:
                raise ValueError(error)
            tokens = conn.execute(
                """
                SELECT password_resets.*, users.id AS user_id
                FROM password_resets
                JOIN users ON users.id = password_resets.user_id
                WHERE password_resets.user_id = ? AND used = 0
                ORDER BY id DESC
                """,
                (user["id"],),
            ).fetchall()
            matched_token = None
            now_value = datetime.now()
            for token in tokens:
                expires_at = token["expires_at"] or ""
                if expires_at:
                    try:
                        if datetime.strptime(expires_at, "%Y-%m-%d %H:%M") < now_value:
                            continue
                    except ValueError:
                        continue
                token_hash = token["token_hash"] or hash_password(token["code"] or "")
                if token_hash == hash_password(code):
                    matched_token = token
                    break
            if not matched_token:
                raise ValueError("Неверный код или срок действия истёк.")
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), matched_token["user_id"]),
            )
            conn.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (matched_token["id"],))
            self._log(conn, "reset_password", "user", matched_token["user_id"], "Пароль был изменён через код восстановления.")
            conn.commit()

    def change_password(self, old_password, new_password):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user:
                raise ValueError("Необходимо войти в систему.")
            if user["password_hash"] != hash_password(old_password):
                raise ValueError("Старый пароль указан неверно.")
            ok, error = check_password_policy(new_password)
            if not ok:
                raise ValueError(error)
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), user["id"]),
            )
            self._log(conn, "change_password", "user", user["id"], "Пользователь сменил пароль.")
            conn.commit()

    def _send_reset_email(self, to_email, reset_code):
        if not self.config:
            raise RuntimeError("Почтовая конфигурация не загружена.")
        message = MIMEText(
            "Ваш код для восстановления пароля: "
            + reset_code
            + "\nКод действует ограниченное время. Никому его не сообщайте.",
            "plain",
            "utf-8",
        )
        message["Subject"] = "SkyNet Mobile: код для восстановления пароля"
        message["From"] = self.config.mailFrom
        message["To"] = to_email
        with smtplib.SMTP(self.config.mailServer, self.config.mailPort, timeout=15) as smtp:
            if self.config.mailUseTls:
                smtp.starttls()
            if self.config.mailUsername:
                smtp.login(self.config.mailUsername, self.config.mailPassword)
            smtp.send_message(message)

    def update_profile(self, login, email, full_name, organization=""):
        login = login.strip()
        email = email.strip().lower()
        full_name = full_name.strip()
        organization = organization.strip()
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user:
                raise ValueError("Необходимо войти в систему.")
            duplicate = conn.execute(
                "SELECT id FROM users WHERE (login = ? OR email = ?) AND id != ?",
                (login, email, user["id"]),
            ).fetchone()
            if duplicate:
                raise ValueError("Логин или email уже используются другим пользователем.")
            conn.execute(
                """
                UPDATE users
                SET login = ?, email = ?, full_name = ?, organization = ?
                WHERE id = ?
                """,
                (login, email, full_name, organization, user["id"]),
            )
            self._log(conn, "update_profile", "user", user["id"], "Обновлён профиль пользователя.")
            conn.commit()
            return self.get_current_user()

    def update_avatar(self, file_path):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user:
                raise ValueError("Необходимо войти в систему.")
            conn.execute("UPDATE users SET avatar_path = ? WHERE id = ?", (str(file_path), user["id"]))
            self._log(conn, "update_avatar", "user", user["id"], "Обновлён путь к аватару.")
            conn.commit()

    def get_client_dashboard_stats(self):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user:
                return {"tickets": 0, "active": 0, "articles": 0}
            ticket_total = conn.execute(
                "SELECT COUNT(*) FROM tickets WHERE author_id = ?",
                (user["id"],),
            ).fetchone()[0]
            ticket_active = conn.execute(
                """
                SELECT COUNT(*)
                FROM tickets
                JOIN statuses ON statuses.id = tickets.status_id
                WHERE tickets.author_id = ? AND statuses.code IN ('new', 'in_progress')
                """,
                (user["id"],),
            ).fetchone()[0]
            article_total = conn.execute("SELECT COUNT(*) FROM knowledge_articles").fetchone()[0]
            return {"tickets": ticket_total, "active": ticket_active, "articles": article_total}

    def get_categories(self):
        with self._connect() as conn:
            return [dict(row) for row in conn.execute("SELECT id, code, name FROM categories ORDER BY name")]

    def get_statuses(self):
        with self._connect() as conn:
            return [dict(row) for row in conn.execute("SELECT id, code, name FROM statuses ORDER BY id")]

    def get_roles(self):
        with self._connect() as conn:
            return [dict(row) for row in conn.execute("SELECT id, code, name FROM roles ORDER BY id")]

    def get_users(self):
        with self._connect() as conn:
            current = self._current_db_user(conn)
            if not current or current["role_code"] != "admin":
                return []
            return [
                {
                    "id": row["id"],
                    "login": row["login"],
                    "email": row["email"],
                    "full_name": row["full_name"],
                    "organization": row["organization"],
                    "role_code": row["role_code"],
                    "role_name": row["role_name"],
                }
                for row in conn.execute(
                    """
                    SELECT users.id, users.login, users.email, users.full_name, users.organization,
                           roles.code AS role_code, roles.name AS role_name
                    FROM users
                    JOIN roles ON roles.id = users.role_id
                    ORDER BY users.full_name
                    """
                )
            ]

    def get_staff_users(self):
        with self._connect() as conn:
            return [
                {
                    "id": row["id"],
                    "full_name": row["full_name"],
                    "role_code": row["role_code"],
                    "role_name": row["role_name"],
                }
                for row in conn.execute(
                    """
                    SELECT users.id, users.full_name, roles.code AS role_code, roles.name AS role_name
                    FROM users
                    JOIN roles ON roles.id = users.role_id
                    WHERE roles.code IN ('operator', 'admin')
                    ORDER BY users.full_name
                    """
                )
            ]

    def create_user(self, login, email, full_name, password, role_code, organization=""):
        with self._connect() as conn:
            current = self._current_db_user(conn)
            if not current or current["role_code"] != "admin":
                raise ValueError("Только администратор может создавать пользователей.")
            role = conn.execute("SELECT id FROM roles WHERE code = ?", (role_code,)).fetchone()
            if not role:
                raise ValueError("Роль не найдена.")
            duplicate = conn.execute("SELECT id FROM users WHERE login = ? OR email = ?", (login, email)).fetchone()
            if duplicate:
                raise ValueError("Пользователь с таким логином или email уже существует.")
            cursor = conn.execute(
                """
                INSERT INTO users(login, email, full_name, password_hash, role_id, organization, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (login.strip(), email.strip().lower(), full_name.strip(), hash_password(password), role["id"], organization.strip(), now_str()),
            )
            self._log(conn, "create_user", "user", cursor.lastrowid, f"Создан пользователь с ролью {role_code}.")
            conn.commit()

    def update_user(self, user_id, login, email, full_name, role_code, organization=""):
        with self._connect() as conn:
            current = self._current_db_user(conn)
            if not current or current["role_code"] != "admin":
                raise ValueError("Только администратор может редактировать пользователей.")
            role = conn.execute("SELECT id FROM roles WHERE code = ?", (role_code,)).fetchone()
            duplicate = conn.execute(
                "SELECT id FROM users WHERE (login = ? OR email = ?) AND id != ?",
                (login.strip(), email.strip().lower(), user_id),
            ).fetchone()
            if duplicate:
                raise ValueError("Логин или email уже используются.")
            conn.execute(
                """
                UPDATE users
                SET login = ?, email = ?, full_name = ?, role_id = ?, organization = ?
                WHERE id = ?
                """,
                (login.strip(), email.strip().lower(), full_name.strip(), role["id"], organization.strip(), user_id),
            )
            self._log(conn, "update_user", "user", user_id, f"Пользователь обновлён, новая роль: {role_code}.")
            conn.commit()

    def delete_user(self, user_id):
        with self._connect() as conn:
            current = self._current_db_user(conn)
            if not current or current["role_code"] != "admin":
                raise ValueError("Только администратор может удалять пользователей.")
            if user_id == current["id"]:
                raise ValueError("Нельзя удалить текущего администратора.")
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self._log(conn, "delete_user", "user", user_id, "Локальный пользователь удалён.")
            conn.commit()

    def _ticket_query(self):
        return """
            SELECT tickets.id, tickets.title, tickets.description, tickets.priority, tickets.organization,
                   tickets.created_at, tickets.updated_at,
                   categories.id AS category_id, categories.code AS category_code, categories.name AS category_name,
                   statuses.code AS status_code, statuses.name AS status_name,
                   author.id AS author_id, author.full_name AS author_name,
                   assignee.id AS assignee_id, assignee.full_name AS assignee_name
            FROM tickets
            JOIN categories ON categories.id = tickets.category_id
            JOIN statuses ON statuses.id = tickets.status_id
            JOIN users author ON author.id = tickets.author_id
            LEFT JOIN users assignee ON assignee.id = tickets.assignee_id
        """

    def _ticket_permissions(self, ticket, current_user):
        if not current_user["is_authenticated"]:
            return {"can_edit_text": False, "can_delete": False, "can_manage": False}
        created = datetime.strptime(ticket["created_at"], "%Y-%m-%d %H:%M")
        within_hour = datetime.now() - created < timedelta(hours=1)
        can_manage = current_user["is_operator"] or current_user["is_admin"]
        can_edit_text = can_manage or (current_user["id"] == ticket["author_id"] and within_hour)
        can_delete = current_user["is_admin"] or can_manage or (current_user["id"] == ticket["author_id"] and within_hour)
        return {
            "can_edit_text": can_edit_text,
            "can_delete": can_delete,
            "can_manage": can_manage,
        }

    def get_tickets(self, search="", category_id=None, status_code="", author_id=None):
        with self._connect() as conn:
            current_user = self.get_current_user()
            params = []
            where = []
            if current_user["is_client"]:
                where.append("author.id = ?")
                params.append(current_user["id"])
            elif not current_user["is_operator"] and not current_user["is_admin"]:
                return []
            if search.strip():
                where.append("(lower(tickets.title) LIKE ? OR lower(tickets.description) LIKE ?)")
                pattern = f"%{search.strip().lower()}%"
                params.extend([pattern, pattern])
            if category_id:
                where.append("categories.id = ?")
                params.append(category_id)
            if status_code:
                where.append("statuses.code = ?")
                params.append(status_code)
            if author_id and current_user["is_admin"]:
                where.append("author.id = ?")
                params.append(author_id)

            query = self._ticket_query()
            if where:
                query += " WHERE " + " AND ".join(where)
            query += " ORDER BY tickets.id DESC"
            tickets = []
            for row in conn.execute(query, params):
                item = dict(row)
                item["priority_name"] = PRIORITY_LABELS.get(item["priority"], item["priority"])
                item["assignee_name"] = item["assignee_name"] or "—"
                item.update(self._ticket_permissions(item, current_user))
                tickets.append(item)
            return tickets

    def get_ticket(self, ticket_id):
        ticket_id = int(ticket_id)
        tickets = self.get_tickets()
        ticket = next((item for item in tickets if item["id"] == ticket_id), None)
        if not ticket:
            return None
        with self._connect() as conn:
            comments = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, author_name, text, created_at FROM comments WHERE ticket_id = ? ORDER BY id",
                    (ticket_id,),
                )
            ]
            attachments = [
                dict(row)
                for row in conn.execute(
                    "SELECT id, filename, path, created_at FROM attachments WHERE ticket_id = ? ORDER BY id DESC",
                    (ticket_id,),
                )
            ]
            ticket["comments"] = comments
            ticket["attachments"] = attachments
        return ticket

    def _ensure_client_for_guest(self, conn, full_name, email, organization):
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
        if existing:
            return existing["id"]
        base_login = (email.split("@")[0] or "guest").replace(" ", ".")
        login = base_login
        suffix = 1
        while conn.execute("SELECT id FROM users WHERE login = ?", (login,)).fetchone():
            suffix += 1
            login = f"{base_login}{suffix}"
        role_id = conn.execute("SELECT id FROM roles WHERE code = 'client'").fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO users(login, email, full_name, password_hash, role_id, organization, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (login, email.strip().lower(), full_name.strip(), hash_password("temp12345"), role_id, organization.strip(), now_str()),
        )
        return cursor.lastrowid

    def create_ticket(self, payload):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if user:
                author_id = user["id"]
            else:
                author_id = self._ensure_client_for_guest(
                    conn,
                    payload.get("full_name", "Гость"),
                    payload.get("email", "guest@example.com"),
                    payload.get("organization", ""),
                )
            status_id = conn.execute("SELECT id FROM statuses WHERE code = 'new'").fetchone()[0]
            cursor = conn.execute(
                """
                INSERT INTO tickets(title, description, author_id, assignee_id, category_id, status_id, priority, organization, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["title"].strip(),
                    payload["description"].strip(),
                    author_id,
                    payload.get("assignee_id"),
                    int(payload["category_id"]),
                    status_id,
                    payload.get("priority", "medium"),
                    payload.get("organization", ""),
                    now_str(),
                    now_str(),
                ),
            )
            ticket_id = cursor.lastrowid
            author_name = payload.get("full_name") or self._user_from_row(
                conn.execute(
                    """
                    SELECT users.*, roles.code AS role_code, roles.name AS role_name
                    FROM users JOIN roles ON roles.id = users.role_id WHERE users.id = ?
                    """,
                    (author_id,),
                ).fetchone()
            )["full_name"]
            conn.execute(
                """
                INSERT INTO comments(ticket_id, author_id, author_name, text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ticket_id, author_id, author_name, "Заявка создана и ожидает обработки.", now_str()),
            )
            self._log(conn, "create_ticket", "ticket", ticket_id, "Создана новая локальная заявка.")
            conn.commit()
            return self.get_ticket(ticket_id)

    def update_ticket(self, ticket_id, **changes):
        with self._connect() as conn:
            current_user = self.get_current_user()
            ticket = self.get_ticket(ticket_id)
            if not ticket:
                raise ValueError("Заявка не найдена.")
            permissions = self._ticket_permissions(ticket, current_user)
            updates = []
            params = []

            if permissions["can_edit_text"]:
                for field in ("title", "description", "organization"):
                    if field in changes and changes[field] is not None:
                        updates.append(f"{field} = ?")
                        params.append(changes[field].strip())

            if permissions["can_manage"]:
                if changes.get("category_id"):
                    updates.append("category_id = ?")
                    params.append(int(changes["category_id"]))
                if changes.get("priority"):
                    updates.append("priority = ?")
                    params.append(changes["priority"])
                if changes.get("assignee_id") is not None:
                    assignee_id = changes["assignee_id"] or None
                    updates.append("assignee_id = ?")
                    params.append(assignee_id)
                if changes.get("status_code"):
                    status = conn.execute("SELECT id FROM statuses WHERE code = ?", (changes["status_code"],)).fetchone()
                    if status:
                        updates.append("status_id = ?")
                        params.append(status["id"])

            if not updates:
                raise ValueError("У вас нет прав на изменение этой заявки.")

            updates.append("updated_at = ?")
            params.append(now_str())
            params.append(ticket_id)
            conn.execute(f"UPDATE tickets SET {', '.join(updates)} WHERE id = ?", params)
            detail_parts = []
            if "status_code" in changes and changes.get("status_code") and changes.get("status_code") != ticket["status_code"]:
                detail_parts.append(f"Статус: {ticket['status_name']} -> {STATUS_LABELS.get(changes['status_code'], changes['status_code'])}")
            if "assignee_id" in changes:
                new_assignee_name = "—"
                if changes.get("assignee_id"):
                    assignee = conn.execute("SELECT full_name FROM users WHERE id = ?", (changes["assignee_id"],)).fetchone()
                    if assignee:
                        new_assignee_name = assignee["full_name"]
                if new_assignee_name != ticket["assignee_name"]:
                    detail_parts.append(f"Исполнитель: {ticket['assignee_name']} -> {new_assignee_name}")
            if "priority" in changes and changes.get("priority") and changes.get("priority") != ticket["priority"]:
                detail_parts.append(
                    f"Приоритет: {PRIORITY_LABELS.get(ticket['priority'], ticket['priority'])} -> {PRIORITY_LABELS.get(changes['priority'], changes['priority'])}"
                )
            if not detail_parts:
                detail_parts.append("Изменены параметры заявки.")
            self._log(conn, "update_ticket", "ticket", ticket_id, " | ".join(detail_parts))
            conn.commit()
            return self.get_ticket(ticket_id)

    def delete_ticket(self, ticket_id):
        with self._connect() as conn:
            ticket = self.get_ticket(ticket_id)
            current_user = self.get_current_user()
            if not ticket:
                raise ValueError("Заявка не найдена.")
            if not self._ticket_permissions(ticket, current_user)["can_delete"]:
                raise ValueError("Недостаточно прав для удаления заявки.")
            conn.execute("DELETE FROM comments WHERE ticket_id = ?", (ticket_id,))
            conn.execute("DELETE FROM attachments WHERE ticket_id = ?", (ticket_id,))
            conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
            self._log(conn, "delete_ticket", "ticket", ticket_id, "Локальная заявка удалена.")
            conn.commit()

    def add_comment(self, ticket_id, text):
        text = text.strip()
        if not text:
            raise ValueError("Комментарий не должен быть пустым.")
        with self._connect() as conn:
            current_user = self.get_current_user()
            author_name = current_user["full_name"] if current_user["is_authenticated"] else "Гость"
            conn.execute(
                """
                INSERT INTO comments(ticket_id, author_id, author_name, text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ticket_id, current_user["id"], author_name, text, now_str()),
            )
            self._log(conn, "add_comment", "ticket", ticket_id, "Добавлен комментарий к заявке.")
            conn.commit()
            return self.get_ticket(ticket_id)

    def add_attachment(self, ticket_id, filename, path=""):
        filename = filename.strip()
        if not filename:
            raise ValueError("Укажите имя вложения.")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO attachments(ticket_id, filename, path, uploaded_by, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ticket_id, filename, path.strip(), self.current_user_id, now_str()),
            )
            self._log(conn, "add_attachment", "ticket", ticket_id, f"Добавлено вложение {filename}.")
            conn.commit()
            return self.get_ticket(ticket_id)

    def get_articles(self, category_code=""):
        with self._connect() as conn:
            query = """
                SELECT knowledge_articles.id, knowledge_articles.title, knowledge_articles.content, knowledge_articles.updated_at,
                       categories.code AS category_code, categories.name AS category_name,
                       users.full_name AS author_name
                FROM knowledge_articles
                JOIN categories ON categories.id = knowledge_articles.category_id
                JOIN users ON users.id = knowledge_articles.created_by
            """
            params = []
            if category_code:
                query += " WHERE categories.code = ?"
                params.append(category_code)
            query += " ORDER BY knowledge_articles.id DESC"
            return [dict(row) for row in conn.execute(query, params)]

    def search_articles(self, query, category_code=""):
        query = (query or "").strip().lower()
        if not query:
            return self.get_articles(category_code)
        with self._connect() as conn:
            params = []
            where = []
            if category_code:
                where.append("categories.code = ?")
                params.append(category_code)
            like = f"%{query}%"
            where.append("(lower(knowledge_articles.title) LIKE ? OR lower(knowledge_articles.content) LIKE ?)")
            params.extend([like, like])

            sql = """
                SELECT knowledge_articles.id, knowledge_articles.title, knowledge_articles.content, knowledge_articles.updated_at,
                       categories.code AS category_code, categories.name AS category_name,
                       users.full_name AS author_name
                FROM knowledge_articles
                JOIN categories ON categories.id = knowledge_articles.category_id
                JOIN users ON users.id = knowledge_articles.created_by
            """
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY knowledge_articles.id DESC"
            rows = [dict(row) for row in conn.execute(sql, params)]

        tokens = [t for t in re.split(r"\\s+", query) if t]

        def score(row):
            title = (row.get("title") or "").lower()
            content = (row.get("content") or "").lower()
            s = 0
            for t in tokens:
                s += 6 * title.count(t)
                s += 2 * content.count(t)
            if title.startswith(query):
                s += 10
            return s

        rows.sort(key=score, reverse=True)
        return self._rerank_articles_with_ai(query, rows)

    def _rerank_articles_with_ai(self, query, rows):
        if not rows or not self.config or not getattr(self.config, "openrouterApiKey", ""):
            return rows

        candidate_rows = rows[:8]
        article_block = "\n\n".join(
            f"ID: {row['id']}\nЗаголовок: {row['title']}\nКатегория: {row['category_name']}\nТекст: {row['content'][:500]}"
            for row in candidate_rows
        )
        prompt = (
            "Ты помогаешь сортировать статьи базы знаний техподдержки.\n"
            "Пользовательский запрос: "
            f"{query}\n\n"
            "Ниже кандидаты. Верни только JSON-массив ID статей в порядке наибольшей релевантности.\n"
            "Если все статьи плохие, всё равно отсортируй лучшие сверху.\n\n"
            f"{article_block}"
        )
        payload = {
            "model": self.config.openrouterKnowledgeModel,
            "messages": [
                {"role": "system", "content": "Отвечай только JSON-массивом чисел без пояснений."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        req = urlrequest.Request(
            f"{self.config.openrouterBaseUrl}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.openrouterApiKey}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://skynet-mobile.local",
                "X-Title": "SkyNet Mobile",
            },
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=20) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, json.JSONDecodeError, ValueError):
            return rows

        try:
            content = data["choices"][0]["message"]["content"].strip()
            ranked_ids = json.loads(content)
            ranked_ids = [int(value) for value in ranked_ids]
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return rows

        by_id = {row["id"]: row for row in rows}
        ranked_rows = [by_id[row_id] for row_id in ranked_ids if row_id in by_id]
        leftovers = [row for row in rows if row["id"] not in ranked_ids]
        return ranked_rows + leftovers

    def get_article(self, article_id):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT knowledge_articles.id, knowledge_articles.title, knowledge_articles.content, knowledge_articles.updated_at,
                       categories.code AS category_code, categories.name AS category_name,
                       users.full_name AS author_name
                FROM knowledge_articles
                JOIN categories ON categories.id = knowledge_articles.category_id
                JOIN users ON users.id = knowledge_articles.created_by
                WHERE knowledge_articles.id = ?
                """,
                (article_id,),
            ).fetchone()
            return dict(row) if row else None

    def add_article(self, title, content, category_code):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user or user["role_code"] not in ("operator", "admin"):
                raise ValueError("Только оператор или администратор может добавлять статьи.")
            category = conn.execute("SELECT id FROM categories WHERE code = ?", (category_code,)).fetchone()
            cursor = conn.execute(
                """
                INSERT INTO knowledge_articles(category_id, title, content, created_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (category["id"], title.strip(), content.strip(), user["id"], now_str()),
            )
            self._log(conn, "add_article", "knowledge", cursor.lastrowid, "Добавлена статья базы знаний.")
            conn.commit()
            return self.get_article(cursor.lastrowid)

    def update_article(self, article_id, title, content, category_code):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user or user["role_code"] not in ("operator", "admin"):
                raise ValueError("Недостаточно прав для изменения статьи.")
            category = conn.execute("SELECT id FROM categories WHERE code = ?", (category_code,)).fetchone()
            conn.execute(
                """
                UPDATE knowledge_articles
                SET title = ?, content = ?, category_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (title.strip(), content.strip(), category["id"], now_str(), article_id),
            )
            self._log(conn, "update_article", "knowledge", article_id, "Статья базы знаний обновлена.")
            conn.commit()
            return self.get_article(article_id)

    def delete_article(self, article_id):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user or user["role_code"] != "admin":
                raise ValueError("Удалять статьи может только администратор.")
            conn.execute("DELETE FROM knowledge_articles WHERE id = ?", (article_id,))
            self._log(conn, "delete_article", "knowledge", article_id, "Статья базы знаний удалена.")
            conn.commit()

    def import_articles(self, raw_text, category_code):
        pieces = [part.strip() for part in raw_text.split("\n\n") if part.strip()]
        created = 0
        for index, chunk in enumerate(pieces, start=1):
            lines = chunk.splitlines()
            title = lines[0].strip("# ").strip() if lines else f"Импортированная статья {index}"
            content = "\n".join(lines[1:]).strip() or chunk
            self.add_article(title, content, category_code)
            created += 1
        return created

    def get_logs(self, page=1, page_size=20):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user or user["role_code"] != "admin":
                return {"items": [], "pages": 1}
            total = conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
            pages = max(1, (total + page_size - 1) // page_size)
            offset = max(page - 1, 0) * page_size
            items = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT logs.id, logs.action, logs.entity_type, logs.entity_id, logs.details, logs.created_at,
                           users.full_name AS actor_name
                    FROM logs
                    LEFT JOIN users ON users.id = logs.actor_id
                    ORDER BY logs.id DESC
                    LIMIT ? OFFSET ?
                    """,
                    (page_size, offset),
                )
            ]
            return {"items": items, "pages": pages}

    def get_ticket_logs(self, ticket_id, limit=10):
        with self._connect() as conn:
            return [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT logs.id, logs.action, logs.details, logs.created_at,
                           users.full_name AS actor_name
                    FROM logs
                    LEFT JOIN users ON users.id = logs.actor_id
                    WHERE logs.entity_type = 'ticket' AND logs.entity_id = ?
                    ORDER BY logs.id DESC
                    LIMIT ?
                    """,
                    (ticket_id, limit),
                )
            ]

    def get_report_stats(self):
        with self._connect() as conn:
            user = self._current_db_user(conn)
            if not user or user["role_code"] not in ("operator", "admin"):
                return {}
            status_stats = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT statuses.name AS label, COUNT(*) AS total
                    FROM tickets
                    JOIN statuses ON statuses.id = tickets.status_id
                    GROUP BY statuses.name
                    ORDER BY statuses.id
                    """
                )
            ]
            category_stats = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT categories.name AS label, COUNT(*) AS total
                    FROM tickets
                    JOIN categories ON categories.id = tickets.category_id
                    GROUP BY categories.name
                    ORDER BY total DESC
                    """
                )
            ]
            assignee_stats = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT COALESCE(users.full_name, 'Без исполнителя') AS label, COUNT(*) AS total
                    FROM tickets
                    LEFT JOIN users ON users.id = tickets.assignee_id
                    GROUP BY COALESCE(users.full_name, 'Без исполнителя')
                    ORDER BY total DESC
                    """
                )
            ]
            totals = {
                "tickets": conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0],
                "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                "articles": conn.execute("SELECT COUNT(*) FROM knowledge_articles").fetchone()[0],
                "logs": conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0],
            }
            return {
                "totals": totals,
                "status_stats": status_stats,
                "category_stats": category_stats,
                "assignee_stats": assignee_stats,
            }

    def export_tickets_csv(self):
        export_dir = self.db_path.parent / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / "tickets_export.csv"
        rows = self.get_tickets()
        with export_path.open("w", newline="", encoding="utf-8") as file:
            writer = DictWriter(
                file,
                fieldnames=[
                    "id",
                    "title",
                    "category_name",
                    "status_name",
                    "priority_name",
                    "author_name",
                    "assignee_name",
                    "created_at",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
        return export_path

    def export_operator_summary(self):
        export_dir = self.db_path.parent / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / "operators_report.csv"
        report = self.get_report_stats()
        with export_path.open("w", newline="", encoding="utf-8") as file:
            writer = DictWriter(file, fieldnames=["operator", "tickets"])
            writer.writeheader()
            for row in report.get("assignee_stats", []):
                writer.writerow({"operator": row["label"], "tickets": row["total"]})
        return export_path

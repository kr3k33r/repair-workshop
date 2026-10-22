import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DEVICES = {
    "washer": {"label": "Стиральная машина", "base": 1600},
    "dishwasher": {"label": "Посудомоечная машина", "base": 1900},
    "dryer": {"label": "Сушильная машина", "base": 2100},
}
ISSUES = {
    "drain": {"label": "Не сливает воду", "add": 0},
    "heat": {"label": "Не нагревает", "add": 500},
    "noise": {"label": "Шумит или вибрирует", "add": 800},
    "unknown": {"label": "Другая неисправность", "add": 300},
}
STATUSES = {"new": "Новая", "progress": "В работе", "done": "Завершена"}


def quote(device, issue):
    if (
        not isinstance(device, str)
        or not isinstance(issue, str)
        or device not in DEVICES
        or issue not in ISSUES
    ):
        raise ValueError("Выберите технику и неисправность из списка.")
    low = DEVICES[device]["base"] + ISSUES[issue]["add"]
    return {
        "min": low,
        "max": low + 1800,
        "device": DEVICES[device]["label"],
        "issue": ISSUES[issue]["label"],
    }


class Workshop:
    def __init__(self, database):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS requests(
                id TEXT PRIMARY KEY, request_key TEXT UNIQUE, fingerprint TEXT, created TEXT,
                name TEXT, contact TEXT, device TEXT, issue TEXT, description TEXT,
                preferred TEXT, low INTEGER, high INTEGER, status TEXT DEFAULT 'new')""")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def submit(self, payload):
        def field(key, minimum, maximum):
            value = payload.get(key)
            if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
                raise ValueError(f"Поле «{key}»: от {minimum} до {maximum} символов.")
            return value.strip()

        name, contact = field("name", 2, 80), field("contact", 5, 100)
        if not (
            re.fullmatch(r"@[A-Za-z][A-Za-z0-9_]{4,31}", contact)
            or re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact)
            or re.fullmatch(r"\+?[\d ()-]{10,24}", contact)
            and 10 <= len(re.sub(r"\D", "", contact)) <= 15
        ):
            raise ValueError("Укажите телефон, email или Telegram @username.")
        device, issue = field("device", 1, 30), field("issue", 1, 30)
        estimate = quote(device, issue)
        description, preferred = field("description", 10, 800), field("preferred", 2, 100)
        key = field("request_key", 8, 100)
        if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", key):
            raise ValueError("Некорректный идентификатор запроса.")
        if payload.get("consent") is not True:
            raise ValueError("Для отправки подтвердите сохранение обращения и контакта.")
        values = [name, contact, device, issue, description, preferred]
        fingerprint = hashlib.sha256(json.dumps(values, ensure_ascii=False).encode()).hexdigest()
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM requests WHERE request_key=?", (key,)).fetchone()
            if old:
                if old["fingerprint"] != fingerprint:
                    raise ValueError(
                        "Этот запрос уже использован для других данных. Обновите форму."
                    )
                return {"id": old["id"], "quote": estimate, "repeated": True}
            identifier = "TR-" + uuid.uuid4().hex[:8].upper()
            db.execute(
                """INSERT INTO requests(id,request_key,fingerprint,created,name,contact,device,issue,description,preferred,low,high)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    identifier,
                    key,
                    fingerprint,
                    datetime.now(timezone.utc).isoformat(),
                    *values,
                    estimate["min"],
                    estimate["max"],
                ),
            )
        return {"id": identifier, "quote": estimate, "repeated": False}

    def listing(self):
        with self.connect() as db:
            rows = [
                dict(r)
                for r in db.execute(
                    "SELECT id,created,name,contact,device,issue,description,preferred,low,high,status FROM requests ORDER BY created DESC LIMIT 200"
                )
            ]
        for row in rows:
            row["device_label"] = DEVICES[row["device"]]["label"]
            row["issue_label"] = ISSUES[row["issue"]]["label"]
        return rows

    def set_status(self, identifier, status):
        if not isinstance(status, str) or status not in STATUSES or not isinstance(identifier, str):
            raise ValueError("Неизвестный статус или номер заявки.")
        with self.connect() as db:
            changed = db.execute(
                "UPDATE requests SET status=? WHERE id=?", (status, identifier)
            ).rowcount
        if not changed:
            raise ValueError("Заявка не найдена.")
        return {"ok": True}

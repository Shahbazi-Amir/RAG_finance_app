"""Local, private staging cache and daily admissions."""
from contextlib import closing
from datetime import datetime
from hashlib import sha256
import json
import os
import sqlite3
import stat
import time
import unicodedata
from zoneinfo import ZoneInfo

from src.phase3.rag_runtime.dispatch_claim_bridge import DispatchClaimDenied

_TEHRAN = ZoneInfo("Asia/Tehran")


def private_database(folder, name):
    info = folder.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
        raise DispatchClaimDenied()
    path = folder / name
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o777 != 0o600:
            raise DispatchClaimDenied()
    finally:
        os.close(fd)
    return path


def normalized_query(query):
    return " ".join(unicodedata.normalize("NFC", query).split())


def account_key(value):
    return sha256(value.strip().lower().encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, folder, ttl_seconds, version, *, clock=time.time):
        self.path = private_database(folder, "response-cache.sqlite3")
        self.ttl = ttl_seconds
        self.version = version
        self.clock = clock
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS response_cache(
                key TEXT PRIMARY KEY, expires REAL NOT NULL, payload TEXT NOT NULL)""")
            conn.execute("CREATE INDEX IF NOT EXISTS cache_expiry ON response_cache(expires)")
            conn.commit()

    def _key(self, query):
        return sha256(json.dumps([normalized_query(query), self.version]).encode()).hexdigest()

    def read(self, query, *, contextual):
        if contextual:
            return None
        with closing(sqlite3.connect(self.path)) as conn:
            row = conn.execute("SELECT payload FROM response_cache WHERE key=? AND expires>?",
                               (self._key(query), self.clock())).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, query, producer, *, contextual):
        # A threaded answer may contain user-specific continuity. Only
        # context-independent answers enter the shared corpus cache.
        if contextual or producer.get("outcome") != "ANSWER" or producer.get("issues") != []:
            return
        payload = {k: producer[k] for k in ("outcome", "issues", "claims", "model", "usage",
                   "semantic_support", "locator_openability") if k in producer}
        # Keep cached material limited to the grounded projection and producer metadata.
        payload["claims"] = [
            {"text": c["text"], "citation": {k: c["citation"][k] for k in ("quote", "chunk_id")}}
            for c in payload["claims"]
        ]
        now = self.clock()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("DELETE FROM response_cache WHERE expires<=?", (now,))
            conn.execute("INSERT OR REPLACE INTO response_cache VALUES (?,?,?)",
                         (self._key(query), now + self.ttl, json.dumps(payload)))


class QuotaExceeded(Exception):
    def __init__(self, quota):
        self.quota = quota


class DailyQuota:
    def __init__(self, folder, config, *, clock=time.time):
        self.path = private_database(folder, "daily-quota.sqlite3")
        self.config = config
        self.clock = clock
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS admissions(
                owner TEXT NOT NULL, day TEXT NOT NULL, operation TEXT NOT NULL,
                PRIMARY KEY(owner,day,operation))""")
            conn.commit()

    def _policy(self, keys):
        default, overrides = self.config()
        matches = [overrides[key] for key in keys if key in overrides]
        # Resolve conflicting aliases conservatively.
        finite = [value for value in matches if value is not None]
        return min(finite) if finite else None if matches else default

    def _day(self):
        return datetime.fromtimestamp(self.clock(), _TEHRAN).date().isoformat()

    @staticmethod
    def _usage(conn, owner, day, limit):
        used = conn.execute("SELECT count(*) FROM admissions WHERE owner=? AND day=?",
                            (owner, day)).fetchone()[0]
        return {"limit": limit, "remaining": None if limit is None else max(0, limit - used)}

    def read(self, owner, keys):
        with closing(sqlite3.connect(self.path)) as conn:
            return self._usage(conn, owner, self._day(), self._policy(keys))

    def reserve(self, owner, keys, payload):
        limit, day = self._policy(keys), self._day()
        operation = sha256(json.dumps([payload[k] for k in (
            "requested_conversation_id", "client_message_id", "idempotency_key")]).encode()).hexdigest()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            current = self._usage(conn, owner, day, limit)
            if conn.execute("SELECT 1 FROM admissions WHERE owner=? AND day=? AND operation=?",
                            (owner, day, operation)).fetchone():
                return
            if current["remaining"] == 0:
                raise QuotaExceeded(current)
            conn.execute("INSERT INTO admissions VALUES(?,?,?)", (owner, day, operation))

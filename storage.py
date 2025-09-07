import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple, Set
import os
from config import DATABASE_PATH, DATA_DIR

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS digests (
  date TEXT PRIMARY KEY,
  data_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saved_articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  section TEXT,
  summary TEXT,
  saved_at TEXT NOT NULL,
  published_date TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_url ON saved_articles(url);
"""

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA foreign_keys=ON;')
    return conn


def init_db() -> None:
    conn = _get_conn()
    try:
        conn.executescript(SCHEMA)
        # Best-effort migration to add published_date if missing
        try:
            conn.execute('ALTER TABLE saved_articles ADD COLUMN published_date TEXT')
        except Exception:
            pass
        conn.commit()
    finally:
        conn.close()


def save_digest(date_str: str, data: Dict[str, Any]) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            'INSERT OR REPLACE INTO digests (date, data_json, created_at) VALUES (?, ?, ?)',
            (date_str, json.dumps(data), datetime.utcnow().isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def get_digest(date_str: str) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.execute('SELECT data_json FROM digests WHERE date = ?', (date_str,))
        row = cur.fetchone()
        if not row:
            return None
        return json.loads(row[0])
    finally:
        conn.close()


def list_digest_dates_between(start_date: str, end_date: str) -> Set[str]:
    conn = _get_conn()
    try:
        cur = conn.execute('SELECT date FROM digests WHERE date BETWEEN ? AND ?', (start_date, end_date))
        return {r[0] for r in cur.fetchall()}
    finally:
        conn.close()


def list_saved_articles() -> List[Dict[str, Any]]:
    conn = _get_conn()
    try:
        cur = conn.execute('SELECT id, title, url, section, summary, saved_at, published_date FROM saved_articles ORDER BY COALESCE(published_date, saved_at) DESC, saved_at DESC')
        out = []
        for id_, title, url, section, summary, saved_at, published_date in cur.fetchall():
            out.append({
                'id': id_, 'title': title, 'url': url, 'section': section or '', 'summary': summary or '', 'saved_at': saved_at, 'published_date': published_date or ''
            })
        return out
    finally:
        conn.close()


def is_article_saved(url: str) -> bool:
    conn = _get_conn()
    try:
        cur = conn.execute('SELECT 1 FROM saved_articles WHERE url = ? LIMIT 1', (url,))
        return cur.fetchone() is not None
    finally:
        conn.close()


def save_article(title: str, url: str, section: str = '', summary: str = '', published_date: str = '') -> None:
    conn = _get_conn()
    try:
        conn.execute(
            'INSERT OR IGNORE INTO saved_articles (title, url, section, summary, saved_at, published_date) VALUES (?, ?, ?, ?, ?, ?)',
            (title, url, section, summary, datetime.utcnow().isoformat(), published_date)
        )
        conn.commit()
    finally:
        conn.close()


def delete_article_by_url(url: str) -> None:
    conn = _get_conn()
    try:
        conn.execute('DELETE FROM saved_articles WHERE url = ?', (url,))
        conn.commit()
    finally:
        conn.close() 
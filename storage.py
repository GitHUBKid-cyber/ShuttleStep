"""Remembers each analysis and who it belongs to, in a small database file next to the code."""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "shuttlestep.db")


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def setup():
    with _connect() as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                owner TEXT NOT NULL,
                created_at TEXT NOT NULL,
                video_name TEXT NOT NULL,
                distance_m REAL,
                top_speed REAL,
                lunges INTEGER
            )"""
        )


def save_analysis(result_id, owner, video_name, stats):
    with _connect() as db:
        db.execute(
            "INSERT INTO analyses VALUES (?, ?, ?, ?, ?, ?, ?)",
            (result_id, owner, datetime.now().isoformat(timespec="minutes"), video_name,
             stats["distance_m"], stats["top_speed"], stats["lunges"]),
        )


def get_analysis(result_id):
    with _connect() as db:
        return db.execute("SELECT * FROM analyses WHERE id = ?", (result_id,)).fetchone()


def list_analyses(owner):
    with _connect() as db:
        return db.execute("SELECT * FROM analyses WHERE owner = ? ORDER BY created_at DESC", (owner,)).fetchall()


def delete_analysis(result_id):
    with _connect() as db:
        db.execute("DELETE FROM analyses WHERE id = ?", (result_id,))


def move_analyses(from_owner, to_owner):
    """Give videos analysed as a guest to the account the guest just signed in with."""
    with _connect() as db:
        db.execute("UPDATE analyses SET owner = ? WHERE owner = ?", (to_owner, from_owner))

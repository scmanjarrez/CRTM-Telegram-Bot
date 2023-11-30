# SPDX-License-Identifier: MIT

# Copyright (c) 2022-2023 scmanjarrez. All rights reserved.
# This work is licensed under the terms of the MIT license.

import sqlite3 as sql
from contextlib import closing

import crtm.utils as ut


def setup_db():
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    uid INTEGER PRIMARY KEY,
                    card TEXT DEFAULT NULL,
                    save INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS transports (
                    type TEXT,
                    PRIMARY KEY (type)
                );

                CREATE TABLE IF NOT EXISTS favorites (
                    uid INTEGER,
                    type TEXT,
                    stop_id TEXT,
                    stop TEXT,
                    FOREIGN KEY (uid) REFERENCES users(uid),
                    FOREIGN KEY (type) REFERENCES transports(type),
                    PRIMARY KEY (uid, type, stop_id)
                );
                """
            )


def cached(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                "SELECT EXISTS ("
                "SELECT 1 "
                "FROM users "
                "WHERE uid = ?"
                ")",
                [uid],
            )
            return cur.fetchone()[0]


def add_user(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute("INSERT INTO users (uid) VALUES (?)", [uid])
            db.commit()


def del_user(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute("DELETE FROM users WHERE uid = ?", [uid])
            db.commit()


def favorites(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                "SELECT type, stop_id, stop "
                "FROM favorites "
                "WHERE uid = ?",
                [uid],
            )
            return cur.fetchall()


def favorite_cached(uid, transport, stop_id):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                "SELECT EXISTS ("
                "SELECT 1 "
                "FROM favorites "
                "WHERE uid = ? AND type = ? AND stop_id = ?"
                ")",
                [uid, transport, stop_id],
            )
            return cur.fetchone()[0]


def add_favorite(uid, transport, stop_id, stop):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                "INSERT OR IGNORE INTO transports (type) VALUES (?)",
                [transport],
            )
            cur.execute(
                "INSERT OR IGNORE INTO favorites "
                "(uid, type, stop_id, stop) "
                "VALUES (?, ?, ?, ?)",
                [uid, transport, stop_id, stop],
            )
            db.commit()


def rename_favorite(uid, transport, stop_id, stop):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                "UPDATE favorites "
                "SET stop = ? "
                "WHERE uid = ? AND type = ? AND stop_id = ?",
                [stop, uid, transport, stop_id],
            )
            db.commit()


def del_favorite(uid, transport, stop_id):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                "DELETE FROM favorites "
                "WHERE uid = ? AND type = ? AND stop_id = ?",
                [uid, transport, stop_id],
            )
            db.commit()


def card(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute("SELECT card FROM users WHERE uid = ?", [uid])
            return cur.fetchone()[0]


def save_card(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute("SELECT save FROM users WHERE uid = ?", [uid])
            return cur.fetchone()[0]


def toggle_card(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                "UPDATE users SET save = NOT save WHERE uid = ?", [uid]
            )
            db.commit()


def add_card(uid, cardn):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute(
                "UPDATE users SET card = ? WHERE uid = ?", [cardn, uid]
            )
            db.commit()


def del_card(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute("UPDATE users SET card = NULL WHERE uid = ?", [uid])
            db.commit()


def del_data(uid):
    with closing(sql.connect(ut.FILES["db"])) as db:
        with closing(db.cursor()) as cur:
            cur.execute("DELETE FROM favorites WHERE uid = ?", [uid])
            cur.execute("DELETE FROM users WHERE uid = ?", [uid])
            db.commit()

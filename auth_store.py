"""Small local user store and signed, expiring login cookies."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie

DB_PATH = os.environ.get('AUTH_DB_PATH', '/tmp/bdris-users.sqlite3' if os.environ.get('DEPLOY_MODE') == '1' else 'users.sqlite3')
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
COOKIE = 'bdris_session'
AGE = 7 * 24 * 3600

def connection():
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, salt TEXT NOT NULL, digest TEXT NOT NULL)')
    return db

def pg_connection():
    import psycopg
    db=psycopg.connect(DATABASE_URL, connect_timeout=8)
    db.execute('CREATE TABLE IF NOT EXISTS bdris_users (username TEXT PRIMARY KEY, salt TEXT NOT NULL, digest TEXT NOT NULL)')
    db.commit()
    return db

def password_digest(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 250000).hex()

def signup(username, password):
    username = username.strip().lower()
    if not (3 <= len(username) <= 40) or not all(c.isascii() and (c.isalnum() or c in '._-') for c in username):
        raise ValueError('ইউজারনেম ৩–৪০ অক্ষরের ইংরেজি অক্ষর/সংখ্যা/._- হতে হবে')
    if len(password) < 10 or len(password) > 128:
        raise ValueError('পাসওয়ার্ড ১০–১২৮ অক্ষরের হতে হবে')
    if username == os.environ.get('APP_USER', '').strip().lower():
        raise ValueError('এই ইউজারনেম আগে ব্যবহার হয়েছে')
    salt = secrets.token_hex(16)
    if DATABASE_URL:
        from psycopg import errors
        try:
            with pg_connection() as db:
                db.execute('INSERT INTO bdris_users VALUES (%s,%s,%s)', (username,salt,password_digest(password,salt)))
        except errors.UniqueViolation:
            raise ValueError('এই ইউজারনেম আগে ব্যবহার হয়েছে') from None
    else:
        try:
            with connection() as db:
                db.execute('INSERT INTO users VALUES (?,?,?)', (username, salt, password_digest(password, salt)))
        except sqlite3.IntegrityError:
            raise ValueError('এই ইউজারনেম আগে ব্যবহার হয়েছে') from None
    return username

def login(username, password):
    username = username.strip().lower()
    # The Render owner remains able to log in without depending on the user database.
    owner = os.environ.get('APP_USER', '').strip().lower()
    owner_pass = os.environ.get('APP_PASSWORD', '')
    if owner and hmac.compare_digest(username, owner) and hmac.compare_digest(password, owner_pass):
        return username
    if DATABASE_URL:
        with pg_connection() as db:
            row=db.execute('SELECT salt,digest FROM bdris_users WHERE username=%s',(username,)).fetchone()
    else:
        with connection() as db:
            row = db.execute('SELECT salt,digest FROM users WHERE username=?', (username,)).fetchone()
    if row and hmac.compare_digest(password_digest(password, row[0]), row[1]):
        return username
    raise ValueError('ইউজারনেম অথবা পাসওয়ার্ড সঠিক নয়')

def cookie_for(username, secret):
    payload = f'{username}|{int(time.time()) + AGE}'
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f'{COOKIE}={payload}.{sig}; HttpOnly; SameSite=Strict; Path=/; Max-Age={AGE}' + ('; Secure' if os.environ.get('DEPLOY_MODE') == '1' else '')

def user_from_cookie(header, secret):
    try:
        jar = SimpleCookie(); jar.load(header or '')
        value = jar[COOKIE].value
        payload, sig = value.rsplit('.', 1)
        username, expires = payload.rsplit('|', 1)
        good = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if int(expires) < time.time() or not hmac.compare_digest(sig, good):
            return None
        return username
    except (KeyError, ValueError, TypeError):
        return None

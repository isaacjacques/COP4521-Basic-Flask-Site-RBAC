"""
Name: Isaac Jacques
Date: 11-09-25
Assignment: Module11 Role Based Access Control
Due Date:11-09-25
About this project:
Assumptions: NA
All work below was performed by Isaac Jacques """
from typing import List, Callable
import sqlite3
from pathlib import Path
from flask import Flask, g, render_template, request
from datetime import datetime
import os

from flask import (
    Flask, g, render_template, request, redirect, url_for, session, flash
)

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "employees.db"

app.secret_key = os.urandom(24)

def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        g.db = conn
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    first_time = not DB_PATH.exists()
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys = ON;")
    db.executescript(
        '''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            phone TEXT NOT NULL,
            security_level INTEGER NOT NULL CHECK (security_level BETWEEN 1 AND 3),
            login_password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS emp_pay_raises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id INTEGER NOT NULL,
            pay_raise_date TEXT NOT NULL,
            raise_amt REAL NOT NULL,
            FOREIGN KEY (emp_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        '''
    )
    if first_time:
        employees = [
            ("PDiana", 34, "123-675-7645", 1, "test123"),
            ("TJones", 68, "895-345-6523", 2, "test123"),
            ("AMath", 29, "428-197-3967", 3, "test123"),
            ("BSmith", 37, "239-567-3498", 2, "test123"),
        ]
        db.executemany(
            "INSERT INTO employees (name, age, phone, security_level, login_password) VALUES (?, ?, ?, ?, ?)",
            employees,
        )
        pay_raises = [
            (1, "2020-01-11", 213.77),
            (2, "2022-04-17", 37.33),
            (3, "2024-09-21", 1324.98),
            (1, "2025-01-31", 67.99),
        ]
        db.executemany(
            "INSERT INTO emp_pay_raises (emp_id, pay_raise_date, raise_amt) VALUES (?, ?, ?)",
            pay_raises,
        )
    db.commit()
    db.close()

def is_int(s):
    try:
        int(s)
        return True
    except (TypeError, ValueError):
        return False

def validate_employee_form(form):
    errors: List[str] = []
    name = (form.get("name") or "").strip()
    age = (form.get("age") or "").strip()
    phone = (form.get("phone") or "").strip()
    security = (form.get("security_level") or "").strip()
    password = (form.get("login_password") or "").strip()

    if not name:
        errors.append("You can not enter in an empty name")

    #age is a whole number > 0 and < 121
    if not is_int(age):
        errors.append("The Age must be a whole number greater than 0 and less than 121.")
    else:
        age_val = int(age)
        if not (0 < age_val < 121):
            errors.append("The Age must be a whole number greater than 0 and less than 121.")

    if not phone:
        errors.append("You can not enter in an empty phone number")

    # Security level is numeric between 1 and 3 
    if not is_int(security):
        errors.append("The SecurityLevel must be a numeric between 1 and 3.")
    else:
        sec_val = int(security)
        if not (1 <= sec_val <= 3):
            errors.append("The SecurityLevel must be a numeric between 1 and 3.")

    if not password:
        errors.append("You can not enter in an empty pwd")

    return (len(errors) == 0, errors)

def validate_pay_raise_form(form):
    errors: List[str] = []
    date_str = (form.get("pay_raise_date") or "").strip()
    amt_str = (form.get("raise_amt") or "").strip()

    # Validate date (YYYY-MM-DD from HTML date input)
    try:
        if not date_str:
            raise ValueError("empty")
        datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        errors.append("The PayRaiseDate must be a valid date in YYYY-MM-DD format.")

    try:
        amt = float(amt_str)
        if amt <= 0:
            raise ValueError("not positive")
    except Exception:
        errors.append("The RaiseAmt must be a real number greater than 0.")

    return (len(errors) == 0, errors)

def login_required(view: Callable):
    from functools import wraps as _wraps
    @_wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def roles_required(*allowed_levels: int):
    def decorator(view: Callable):
        from functools import wraps as _wraps
        @_wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            user_level = int(session.get("security_level", 0))
            if allowed_levels and user_level not in allowed_levels:
                return render_template("result.html", msg="Page not found")
            return view(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        db = get_db()
        row = db.execute(
            "SELECT id, name, security_level, login_password FROM employees WHERE name = ?",
            (username,),
        ).fetchone()

        if row and password == row["login_password"]:
            session["user_id"] = int(row["id"])
            session["username"] = row["name"]
            session["security_level"] = int(row["security_level"])
            #flash("Welcome, you have successfully logged in.", "success")
            return redirect(url_for("home"))
        else:
            flash("invalid username and/or password!", "danger")
            return render_template("login.html", bad_login=True, username=username)

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/enternew")
@roles_required(1)
def enternew():
    return render_template("enternew.html")

@app.route("/addrec", methods=["POST"])
@roles_required(1)
def addrec():
    ok, errors = validate_employee_form(request.form)
    if not ok:
        msg = "Query Result :\n" + "\n".join(errors)
        return render_template("result.html", msg=msg)

    db = get_db()
    db.execute(
        "INSERT INTO employees (name, age, phone, security_level, login_password) VALUES (?, ?, ?, ?, ?)",
        (
            request.form["name"].strip(),
            int(request.form["age"]),
            request.form["phone"].strip(),
            int(request.form["security_level"]),
            request.form["login_password"].strip(),
        ),
    )
    db.commit()
    msg = "Query Result : Record successfully added"
    return render_template("result.html", msg=msg)

@app.route("/list")
@roles_required(1, 2)
def list_employees():
    db = get_db()
    rows = db.execute(
        "SELECT id, name, age, phone, security_level, login_password FROM employees ORDER BY id ASC"
    ).fetchall()
    return render_template("list.html", rows=rows)

@app.route("/listPayRaises")
@roles_required(2) 
def list_pay_raises():
    db = get_db()
    rows = db.execute(
        "SELECT id as pay_raise_id, emp_id, pay_raise_date, raise_amt FROM emp_pay_raises ORDER BY id ASC"
    ).fetchall()
    return render_template("list_pay_raises.html", rows=rows)

@app.route("/showMyPayRaises")
@login_required
def show_my_pay_raises():
    uid = int(session["user_id"])
    db = get_db()
    rows = db.execute(
        "SELECT pay_raise_date, raise_amt FROM emp_pay_raises WHERE emp_id = ? ORDER BY pay_raise_date DESC",
        (uid,),
    ).fetchall()
    return render_template("show_my_raises.html", rows=rows)

@app.route("/enterRaise")
@login_required
def enter_raise():
    return render_template("enter_raise.html")

@app.route("/addPayRaise", methods=["POST"])
@login_required
def add_pay_raise():
    ok, errors = validate_pay_raise_form(request.form)
    if not ok:
        msg = "Query Result :\n" + "\n".join(errors)
        return render_template("result.html", msg=msg)

    uid = int(session["user_id"])
    db = get_db()
    db.execute(
        "INSERT INTO emp_pay_raises (emp_id, pay_raise_date, raise_amt) VALUES (?, ?, ?)",
        (
            uid,
            request.form["pay_raise_date"].strip(),
            float(request.form["raise_amt"]),
        ),
    )
    db.commit()
    msg = "Query Result : Pay raise successfully added"
    return render_template("result.html", msg=msg)

@app.route("/result")
def result_page():
    return render_template("result.html", msg="Nothing to show yet. Try adding a new employee.")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
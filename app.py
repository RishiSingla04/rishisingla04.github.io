import os
import csv
import io
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, g, flash, Response, jsonify
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "tracker.db"))
FAMILY_PASSCODE = os.environ.get("FAMILY_PASSCODE", "Singla123")


# ---------------------------------------------------------------- database

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            cost_price REAL NOT NULL,
            quantity_in_stock INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            sale_price REAL NOT NULL,
            quantity_sold INTEGER NOT NULL,
            sold_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (id)
        );
        """
    )
    db.commit()
    db.close()


# ---------------------------------------------------------------- auth

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("passcode") == FAMILY_PASSCODE:
            session["authed"] = True
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Wrong passcode. Try again.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- helpers

def fetch_products():
    return get_db().execute(
        "SELECT * FROM products ORDER BY name COLLATE NOCASE"
    ).fetchall()


def fetch_inventory_summary():
    rows = get_db().execute(
        """
        SELECT
            p.id,
            p.name,
            p.cost_price,
            p.quantity_in_stock,
            COALESCE(SUM(s.quantity_sold), 0) AS units_sold,
            COALESCE(SUM((s.sale_price - p.cost_price) * s.quantity_sold), 0) AS profit
        FROM products p
        LEFT JOIN sales s ON s.product_id = p.id
        GROUP BY p.id
        ORDER BY p.name COLLATE NOCASE
        """
    ).fetchall()
    return rows


# ---------------------------------------------------------------- routes

@app.route("/")
@login_required
def dashboard():
    inventory = fetch_inventory_summary()
    total_profit = sum(r["profit"] for r in inventory)
    total_units_sold = sum(r["units_sold"] for r in inventory)
    total_stock_value = sum(r["cost_price"] * r["quantity_in_stock"] for r in inventory)
    return render_template(
        "dashboard.html",
        inventory=inventory,
        total_profit=total_profit,
        total_units_sold=total_units_sold,
        total_stock_value=total_stock_value,
    )


@app.route("/products/new", methods=["GET", "POST"])
@login_required
def add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            cost_price = float(request.form.get("cost_price", ""))
            quantity = int(request.form.get("quantity", ""))
        except ValueError:
            flash("Cost and quantity must be numbers.")
            return redirect(url_for("add_product"))

        if not name or cost_price < 0 or quantity < 0:
            flash("Please fill in a valid name, cost, and quantity.")
            return redirect(url_for("add_product"))

        db = get_db()
        existing = db.execute(
            "SELECT id FROM products WHERE name = ?", (name,)
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE products SET cost_price = ?, quantity_in_stock = quantity_in_stock + ? WHERE id = ?",
                (cost_price, quantity, existing["id"]),
            )
            flash(f'Added {quantity} to existing stock of "{name}".')
        else:
            db.execute(
                "INSERT INTO products (name, cost_price, quantity_in_stock, created_at) VALUES (?, ?, ?, ?)",
                (name, cost_price, quantity, datetime.now(timezone.utc).isoformat()),
            )
            flash(f'Added new product "{name}".')
        db.commit()
        return redirect(url_for("dashboard"))

    return render_template("add_product.html")


@app.route("/sales/new", methods=["GET", "POST"])
@login_required
def record_sale():
    products = fetch_products()

    if request.method == "POST":
        try:
            product_id = int(request.form.get("product_id", ""))
            sale_price = float(request.form.get("sale_price", ""))
            quantity = int(request.form.get("quantity", ""))
        except ValueError:
            flash("Please fill in all fields with valid numbers.")
            return redirect(url_for("record_sale"))

        db = get_db()
        product = db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()

        if not product:
            flash("Select a product.")
            return redirect(url_for("record_sale"))
        if quantity <= 0 or sale_price < 0:
            flash("Quantity must be at least 1 and price can't be negative.")
            return redirect(url_for("record_sale"))
        if quantity > product["quantity_in_stock"]:
            flash(f'Only {product["quantity_in_stock"]} left in stock for "{product["name"]}".')
            return redirect(url_for("record_sale"))

        db.execute(
            "INSERT INTO sales (product_id, sale_price, quantity_sold, sold_at) VALUES (?, ?, ?, ?)",
            (product_id, sale_price, quantity, datetime.now(timezone.utc).isoformat()),
        )
        db.execute(
            "UPDATE products SET quantity_in_stock = quantity_in_stock - ? WHERE id = ?",
            (quantity, product_id),
        )
        db.commit()
        flash(f'Sale recorded: {quantity} x "{product["name"]}".')
        return redirect(url_for("dashboard"))

    return render_template("record_sale.html", products=products)


@app.route("/export.csv")
@login_required
def export_csv():
    db = get_db()
    rows = db.execute(
        """
        SELECT s.sold_at, p.name, s.sale_price, s.quantity_sold, p.cost_price,
               (s.sale_price - p.cost_price) * s.quantity_sold AS profit
        FROM sales s
        JOIN products p ON p.id = s.product_id
        ORDER BY s.sold_at DESC
        """
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Product", "Sale Price", "Quantity", "Cost Price", "Profit"])
    for r in rows:
        writer.writerow([r["sold_at"], r["name"], r["sale_price"], r["quantity_sold"], r["cost_price"], r["profit"]])

    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_export.csv"},
    )


@app.route("/api/chart-data")
@login_required
def chart_data():
    days = int(request.args.get("days", 30))
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    db = get_db()
    rows = db.execute(
        """
        SELECT
            substr(s.sold_at, 1, 10) AS day,
            SUM(s.quantity_sold) AS units,
            SUM((s.sale_price - p.cost_price) * s.quantity_sold) AS profit
        FROM sales s
        JOIN products p ON p.id = s.product_id
        WHERE s.sold_at >= ?
        GROUP BY day
        ORDER BY day ASC
        """,
        (since,),
    ).fetchall()

    return jsonify(
        {
            "labels": [r["day"] for r in rows],
            "units": [r["units"] for r in rows],
            "profit": [round(r["profit"], 2) for r in rows],
        }
    )


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

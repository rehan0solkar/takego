from flask import Flask, render_template, request, session, redirect, jsonify, flash, url_for
import sqlite3
import os, uuid
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash, check_password_hash

def hash_pw(pw):
    return generate_password_hash(pw)

def check_pw(raw_password, hashed_password):
    return check_password_hash(hashed_password, raw_password)

def current_user():
    sid = session.get("active_sid")
    if not sid:
        return None
    sessions = session.get("sessions", {})
    user = sessions.get(sid)
    if not user:
        return None

    # 🔥 ADD THIS (backward compatibility ke liye)
    if "user" not in user:
        # id / user_id jo bhi hai uske hisaab se
        if "id" in user:
            user["user"] = user["id"]
        elif "user_id" in user:
            user["user"] = user["user_id"]
    return user
#Eta timer
def apply_eta_queue(orders):
    now = datetime.now(timezone.utc)
    cumulative_minutes = 0
    final = []

    for o in orders:
        o = dict(o)
        if o["status"] not in ("pending", "accepted"):
            o["remaining"] = None
            o["ready_at"] = None
            final.append(o)
            continue

        if o.get("prep_time") and o.get("accepted_at"):
            prep = int(o["prep_time"])
            cumulative_minutes += prep
            accepted = datetime.fromisoformat(
                o["accepted_at"]
            ).replace(tzinfo=timezone.utc)

            ready_at = accepted + timedelta(minutes=cumulative_minutes)
            remaining = max(0, int((ready_at - now).total_seconds() // 60))

            o["remaining"] = remaining
            o["ready_at"] = ready_at.isoformat()
        else:
            o["remaining"] = None
            o["ready_at"] = None

        final.append(o)

    return final


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")
def get_db():
    conn = sqlite3.connect("database.db", timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    return render_template("home.html")

@app.context_processor
def inject_current_user():
    return dict(current_user=current_user)

# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return jsonify(success=False, error="Fill all fields")

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()
    db.close()

    if not user or not check_pw(password, user["password"]):
        return jsonify(success=False, error="Invalid username or password")

    # ✅ session set
    sid = str(uuid.uuid4())
    session["active_sid"] = sid
    session["user_id"] = user["id"]
    session.setdefault("sessions", {})[sid] = {
        "id": user["id"],
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"]
    }

    # ✅ tell frontend where to go
    redirect_url = "/customer" if user["role"] == "customer" else "/owner"

    return jsonify(success=True, redirect=redirect_url)

# ================= REGISTER OWNER =================
@app.route("/register_owner", methods=["GET", "POST"])
def register_owner():
    if request.method == "GET":
        return render_template("register_owner.html")

    username = request.form.get("username")
    password = hash_pw(request.form.get("password"))
    stall_name = request.form.get("stall_name")
    product_name = request.form.get("product_name")

    try:
        price = int(request.form.get("price", 0))
        prep_time = int(request.form.get("prep_time", 0))
        availability = int(request.form.get("availability", 0))
    except ValueError:
        return render_template("register_owner.html", error="Invalid input")

    if not all([username, password, stall_name, product_name]):
        return render_template("register_owner.html", error="Missing fields")

    if price <= 0 or prep_time <= 0 or availability <= 0 or len(request.form.get("password")) < 8:
        return render_template("register_owner.html", error="Invalid values")

    image_name = None
    image = request.files.get("product_image")
    if image and image.filename:
        os.makedirs("static/uploads", exist_ok=True)
        image_name = image.filename
        image.save(os.path.join("static/uploads", image_name))

    db = get_db()
    try:
        if db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone():
            return render_template("register_owner.html", error="Username exists")
        db.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, 'owner')",
            (username, password)
        )

        owner_id = db.execute(
            "SELECT id FROM users WHERE username=?", (username,)
        ).fetchone()[0]

        db.execute(
            "INSERT INTO stalls (stall_name, owner_id) VALUES (?, ?)",
            (stall_name, owner_id)
        )

        stall_id = db.execute(
            "SELECT id FROM stalls WHERE owner_id=?", (owner_id,)
        ).fetchone()[0]

        db.execute("""
            INSERT INTO products
            (stall_id, product_name, price, prep_time, availability, image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (stall_id, product_name, price, prep_time, availability, image_name))

        db.commit()
    finally:
        db.close()

    return redirect("/login")


# ================= REGISTER CUSTOMER =================
@app.route("/register_customer", methods=["GET", "POST"])
def register_customer():
    if request.method == "GET":
        return render_template("register_customer.html")

    username = request.form.get("username")
    raw_password = request.form.get("password")
    confirm = request.form.get("confirm")
    if not username:
        return jsonify(success=False, error="Fill username")
    if not raw_password:
        return jsonify(success=False, error="Fill password")
    if not confirm:
        return jsonify(success=False, error="Fill confirm password")
    if len(raw_password) < 8:
        return jsonify(success=False, error="Password must be at least 8 characters")
    if raw_password != confirm:
        return jsonify(success=False, error="Password and confirm password do not match")
    password = hash_pw(raw_password)
    db = get_db()
    try:
        if db.execute(
        "SELECT id FROM users WHERE username=?",
        (username,)
        ).fetchone():
            return jsonify(success=False, error="Username exists")
        db.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, 'customer')",
        (username, password)
    )
        db.commit()
    finally:
        db.close()
    return jsonify(success=True)

# ================= CUSTOMER =================
@app.route("/customer")
def customer():
    user = current_user()
    if not user or user["role"] != "customer":
        return redirect("/login")
    db = get_db()
    stalls = db.execute("""
        SELECT id, stall_name
        FROM stalls
    """).fetchall()
    db.close()
    return render_template("customer.html", stalls=stalls)

# STALL PRODUCTS
@app.route("/stall/<int:stall_id>")
def stall_products(stall_id):
    user = current_user()
    if not user or user["role"] != "customer":
        return redirect("/login")
    db = get_db()
    products = db.execute("""
        SELECT id, product_name, price, prep_time, availability, image
        FROM products
        WHERE stall_id=?
        ORDER BY id ASC
    """, (stall_id,)).fetchall()
    db.close()

    return render_template("stall_products.html", products=products)


# ================= OWNER =================
@app.route("/owner")
def owner():
    if not current_user() or current_user()["role"] != "owner":
        return redirect("/login")

    db = get_db()
    try:
        products = db.execute("""
            SELECT p.id, p.product_name, p.price, p.prep_time,
                   p.availability, p.image
            FROM products p
            JOIN stalls s ON p.stall_id = s.id
            JOIN users u ON s.owner_id = u.id
            WHERE u.id=?
        """, (current_user()["id"],)).fetchall()
    finally:
        db.close()

    return render_template("owner.html", products=products)


# ================= ADD PRODUCT =================
@app.route("/add_product", methods=["POST"])
def add_product():
    user = current_user()
    if not user:
        return redirect("/login")

    name = request.form.get("product_name")
    price = int(request.form.get("price", 0))
    prep = int(request.form.get("prep_time", 0))
    avail = int(request.form.get("availability", 0))

    if not name or price <= 0 or prep <= 0 or avail <= 0:
        return redirect("/owner")

    image_name = None
    image = request.files.get("product_image")
    if image and image.filename:
        os.makedirs("static/uploads", exist_ok=True)
        image_name = image.filename
        image.save(os.path.join("static/uploads", image_name))

    db = get_db()
    try:
        owner_id = user.get("id")
        row = db.execute(
            "SELECT id FROM stalls WHERE owner_id=?",
            (owner_id,)
        ).fetchone()
        if row is None:
            return "Stall not found", 400
        stall_id = row[0]
        db.execute("""
            INSERT INTO products
            (stall_id, product_name, price, prep_time, availability, image)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (stall_id, name, price, prep, avail, image_name))
        db.commit()
    finally:
        db.close()

    return redirect("/owner")


# ================= GENERATE TOKEN =================
@app.route("/generate_token", methods=["POST"])
def generate_token():
    user = current_user()
    if not user or user["role"] != "customer":
        flash("Please login first", "error")
        return jsonify(success=False)


    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity", 1))

    db = get_db()
    try:
        db.execute("BEGIN")

        product = db.execute("""
            SELECT id, stall_id, price, availability
            FROM products
            WHERE id=?
        """, (product_id,)).fetchone()

        if not product:
            db.rollback()
            flash("Product not found", "error")
            return jsonify(success=False)

        if product["availability"] < quantity:
            db.rollback()
            flash("Not enough quantity available", "error")
            return jsonify(success=False)

        token = db.execute("""
            SELECT COALESCE(MAX(token),0)+1
            FROM orders
            WHERE stall_id=?
        """, (product["stall_id"],)).fetchone()[0]

        db.execute("""
            INSERT INTO orders (customer_id, stall_id, price, token)
            VALUES (?, ?, ?, ?)
        """, (user["id"], product["stall_id"], product["price"] * quantity, token))

        order_id = db.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        db.execute("""
            INSERT INTO order_items (order_id, product_id, quantity)
            VALUES (?, ?, ?)
        """, (order_id, product_id, quantity))

        db.execute("""
            UPDATE products
            SET availability = availability - ?
            WHERE id=? AND availability >= ?
        """, (quantity, product_id, quantity))

        db.commit()
        flash(f"Token no. {token}", "success")
        return jsonify(success=True, token=token)

    except Exception:
        db.rollback()
        flash("Something went wrong. Try again.", "error")
        return jsonify(success=False)

    finally:
        db.close()

# ================= OWNER ORDERS =================
@app.route("/owner_orders")
def owner_orders():
    if not current_user() or current_user()["role"] != "owner":
        return redirect("/login")

    db = get_db()
    try:
        orders = db.execute("""
    SELECT
        o.id,
        o.token,
        o.status,
        o.accepted_at,
        o.remaining,
        SUM(oi.quantity * p.price) AS total_price,
        GROUP_CONCAT(p.product_name || ' x ' || oi.quantity) AS items,
        SUM(p.prep_time * oi.quantity) AS prep_time
    FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.id
LEFT JOIN products p ON p.id = oi.product_id
    JOIN stalls s ON o.stall_id = s.id
    WHERE s.owner_id = ?
    AND o.status IN ('pending','accepted','rejected','ready','cancelled')
GROUP BY
        o.id
ORDER BY
    CASE o.status
        WHEN 'pending' THEN 1
        WHEN 'accepted' THEN 1
        WHEN 'ready' THEN 2
        WHEN 'cancelled' THEN 3
        WHEN 'rejected' THEN 3
    END,
    o.id DESC
        """, (current_user()["id"],)).fetchall()

        orders_with_eta = []
        orders_with_eta = apply_eta_queue(orders)
        order_items = {}

        for o in orders_with_eta:
            items = db.execute("""
            SELECT p.product_name, oi.quantity, p.image
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id=?
            """, (o["id"],)).fetchall()
            order_items[o["id"]] = items

    finally:
        db.close()

    return render_template("owner_orders.html", orders=orders_with_eta, order_items=order_items)


# AUTO REFRESH
@app.route("/owner_orders_partial")
def owner_orders_partial():
    user = current_user()
    if not user or user["role"] != "owner":
        return ""
    db = get_db()

    orders = db.execute("""
       SELECT
        o.id,
        o.token,
        o.status,
        o.accepted_at,
        o.remaining,
        SUM(oi.quantity * p.price) AS total_price,
        GROUP_CONCAT(p.product_name || ' x ' || oi.quantity) AS items,
        SUM(p.prep_time * oi.quantity) AS prep_time
    FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.id
LEFT JOIN products p ON p.id = oi.product_id
    JOIN stalls s ON o.stall_id = s.id
    WHERE s.owner_id = ?
    AND o.status IN ('pending','accepted','rejected','ready','cancelled')
GROUP BY
        o.id
ORDER BY
    CASE o.status
        WHEN 'pending' THEN 1
        WHEN 'accepted' THEN 1
        WHEN 'ready' THEN 2
        WHEN 'cancelled' THEN 3
        WHEN 'rejected' THEN 3
    END,
    o.id DESC
    """, (user["id"],)).fetchall()
    orders_with_eta = []
    orders_with_eta = apply_eta_queue(orders)
    db.close()
    return render_template(
        "owner_orders_partial.html",
        orders=orders_with_eta
    )

# ACCEPT ORDER
@app.route("/accept_order/<int:order_id>", methods=["POST"])
def accept_order(order_id):
    db = get_db()
    order = db.execute("""
        SELECT id FROM orders
        WHERE id=? AND status='pending'
    """, (order_id,)).fetchone()

    if order:
        db.execute("""
    UPDATE orders
    SET status = 'accepted',
        accepted_at = CURRENT_TIMESTAMP
    WHERE id = ?
        """, (order_id,))
        db.commit()

    db.close()
    return redirect("/owner_orders")

# TOKEN COUNTER 
@app.route("/current_token")
def current_token():
    db = get_db()
    try:
        stall_id = request.args.get("stall_id")
        if not stall_id:
            return jsonify({"token": 0})

        row = db.execute(
            "SELECT COALESCE(MAX(token),0) FROM orders WHERE stall_id=?",
            (stall_id,)
        ).fetchone()
        return jsonify({"token": row[0]})
    finally:
        db.close()

# ================= UPDATE ORDER STATUS =================
@app.route("/update_order_status/<int:order_id>/<status>")
def update_order_status(order_id, status):
    user = current_user()
    if not user or user["role"] != "owner":
        return redirect("/login")

    if status not in ("accepted", "rejected", "ready"):
        return redirect("/owner_orders")

    db = get_db()
    order = db.execute(
        "SELECT status FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()
    if not order or order["status"] == "cancelled":
        db.close()
        return redirect("/owner_orders")

    # 1️⃣ PENDING → ACCEPTED
    if order["status"] == "pending" and status == "accepted":
        db.execute(
            """
            UPDATE orders
            SET status = 'accepted',
                accepted_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (order_id,)
        )

    # 2️⃣ PENDING → REJECTED
    elif order["status"] == "pending" and status == "rejected":
        db.execute(
            """
            UPDATE orders
            SET status = 'rejected'
            WHERE id = ?
            """,
            (order_id,)
        )

    # 3️⃣ ACCEPTED → READY
    elif order["status"] == "accepted" and status == "ready":
        db.execute(
            """
            UPDATE orders
            SET status = 'ready'
            WHERE id = ?
            """,
            (order_id,)
        )
    db.commit()
    db.close()
    return redirect("/owner_orders")

# ORDER HISTORY
@app.route("/order_history")
def order_history():
    user=current_user()
    if not user or user["role"] != "customer":
        return redirect("/login")

    db = get_db()    
    orders = db.execute("""
        SELECT 
        o.id,
        o.token,
        o.status,
        SUM(oi.quantity * p.price) AS total_price,
        o.accepted_at,
        o.remaining,
        GROUP_CONCAT(p.product_name || ' x' || oi.quantity) AS items,
        SUM(p.prep_time * oi.quantity) AS prep_time
    FROM orders o
    JOIN order_items oi ON oi.order_id = o.id
    JOIN products p ON p.id = oi.product_id
    WHERE o.customer_id = ?
    GROUP BY
        o.id
ORDER BY
    CASE o.status
        WHEN 'ready' THEN 1
        WHEN 'pending' THEN 2
        WHEN 'accepted' THEN 2
        WHEN 'cancelled' THEN 3
        WHEN 'rejected' THEN 3
    END,
    o.id DESC
    """, (current_user()["id"],)).fetchall()
    orders_with_eta = []

# 👉 accepted order ke hisaab se sort
    orders_with_eta = apply_eta_queue(orders)

    order_items = {}

    for o in orders_with_eta:
        items = db.execute("""
            SELECT p.product_name, oi.quantity, p.image
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id=?
        """, (o["id"],)).fetchall()

        order_items[o["id"]] = items


    db.close()

    return render_template(
        "your_orders.html",
        orders=orders_with_eta,
        order_items=order_items
    )


# UPDATE product
@app.route("/update_product/<int:pid>", methods=["GET", "POST"])
def update_product(pid):
    if not current_user() or current_user()["role"] != "owner":
        return redirect("/login")

    db = get_db()

    if request.method == "GET":
        product = db.execute(
            "SELECT id, product_name, price, prep_time, availability FROM products WHERE id=?",
            (pid,)
        ).fetchone()
        db.close()

        if not product:
            return "Product not found", 404

        return render_template("edit_product.html", p=product)

    # POST
    product_name = request.form.get("product_name")
    price = int(request.form.get("price", 0))
    prep_time = int(request.form.get("prep_time", 0))
    availability = int(request.form.get("availability", 0))

    db.execute("""
        UPDATE products
        SET product_name=?, price=?, prep_time=?, availability=?
        WHERE id=?
    """, (product_name, price, prep_time, availability, pid))

    db.commit()
    db.close()

    return redirect("/owner")


# DELETE PRODUCT
@app.route("/delete_product/<int:pid>")
def delete_product(pid):
    if not current_user() or current_user()["role"] != "owner":
        return redirect("/login")

    db = get_db()
    db.execute("DELETE FROM order_items WHERE product_id=?", (pid,))
    db.execute("DELETE FROM products WHERE id=?", (pid,))

    db.commit()
    db.close()

    return redirect("/owner")

# CANCEL ORDER
@app.route("/cancel_order/<int:order_id>", methods=["POST"])
def cancel_order(order_id):
    if not current_user():
        return redirect("/login")

    db = get_db()
    try:
        order = db.execute("""
            SELECT status FROM orders
            WHERE id=? AND customer_id=? AND status='pending' 
        """, (order_id, current_user()["id"])).fetchone()

        if not order or order[0] != "pending":
            return redirect("/order_history")

        items = db.execute("""
            SELECT product_id, quantity
            FROM order_items
            WHERE order_id=?
        """, (order_id,)).fetchall()

        for pid, qty in items:
            db.execute("""
                UPDATE products
                SET availability = availability + ?
                WHERE id=?
            """, (qty, pid))

        db.execute("""
            UPDATE orders
            SET status='cancelled'
            WHERE id=?
        """, (order_id,))

        db.commit()
    finally:
        db.close()

    return redirect("/order_history")

@app.route("/logout")
def logout():
    user = current_user()
    if not user:
        return redirect("/login")

    sid = session.get("active_sid")
    if sid and "sessions" in session:
        session["sessions"].pop(sid, None)
    session.pop("active_sid", None)
    return redirect("/login")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


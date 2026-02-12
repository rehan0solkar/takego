import sqlite3

db = sqlite3.connect("database.db")
db.execute("PRAGMA foreign_keys = ON")

# ================= USERS =================
db.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT CHECK(role IN ('customer','owner')) NOT NULL,
    terms_accepted BOOLEAN DEFAULT 0,
    is_active INTEGER DEFAULT 1 
)
""")

# ================= STALLS =================
db.execute("""
CREATE TABLE IF NOT EXISTS stalls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    stall_name TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE RESTRICT
)
""")

# ================= PRODUCTS =================
db.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stall_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price INTEGER NOT NULL,
    prep_time INTEGER NOT NULL,
    availability INTEGER CHECK(availability >= 0) DEFAULT 1,
    image TEXT,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY(stall_id) REFERENCES stalls(id) ON DELETE RESTRICT
)
""")

# ================= ORDERS =================
db.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    stall_id INTEGER NOT NULL,
    price INTEGER,
    token INTEGER NOT NULL,
    status TEXT CHECK(
        status IN ('pending','accepted','rejected','ready','cancelled')
    ) DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    accepted_at DATETIME,
    prep_time INTEGER,
    is_deleted INTEGER DEFAULT 0,
    FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY(stall_id) REFERENCES stalls(id) ON DELETE RESTRICT,
    UNIQUE(stall_id, token)
)
""")

# ================= ORDER ITEMS =================
db.execute("""
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER CHECK(quantity > 0) DEFAULT 1,
    FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE RESTRICT
)
""")

# ================= REFRESH TOKENS =================
db.execute("""
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    sid TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE RESTRICT
)
""")

db.commit()
db.close()

print("Database.db is created")

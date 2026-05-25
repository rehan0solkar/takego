# 🍔 TakeGo

TakeGo is a modern food stall ordering platform built using Flask and SQLite.  
The platform allows customers to browse stalls, place food orders, and track order status, while stall owners can manage products and incoming orders through a dedicated dashboard.

---

# 🚀 Live Demo

https://takego.pythonanywhere.com

---

# ✨ Features

## 👤 Authentication System
- JWT-based authentication
- Access Token + Refresh Token system
- Multi-session login support
- Role-based login (Customer / Owner)
- Secure password handling

---

## 🛒 Customer Features
- Browse food stalls
- View products and prices
- Place orders
- Track order status
- Token-based ordering system

---

## 🏪 Stall Owner Features
- Create and manage stalls
- Add / Edit / Delete products
- Accept or reject orders
- Update preparation status
- Manage product availability

---

# 🔐 Authentication Flow

The project uses a dual-token JWT authentication system.

### Access Token
- Short-lived token
- Used for request authentication
- Improves security

### Refresh Token
- Long-lived token
- Stored in database
- Generates new access tokens automatically
- Supports multi-device login sessions

---

# 🗄 Database Tables

| Table | Purpose |
|---|---|
| users | Stores user account details |
| stalls | Stores stall information |
| products | Stores product details |
| orders | Stores customer orders |
| order_items | Stores ordered products |
| refresh_tokens | Stores active login sessions |

---

# 🛠 Tech Stack

## Backend
- Flask
- SQLite
- PyJWT

## Frontend
- HTML
- CSS
- Bootstrap
- Jinja2

---

# 📂 Project Structure

```bash
take-go/
│
├── main.py
├── db.py
├── database.db
├── requirements.txt
│
├── static/
│
└── templates/
```

---

# ⚙️ Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/take-go.git
cd take-go
```

---

## 2️⃣ Create Virtual Environment

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Setup Database

```bash
python db.py
```

---

## 5️⃣ Run Application

```bash
python main.py
```

---

# 🌐 Deployment

The project is deployed using:

- PythonAnywhere
- Flask WSGI Configuration
- SQLite Database

---

# 🔮 Future Improvements

- Online payment integration
- Real-time notifications
- Admin dashboard
- Mobile responsive redesign
- Analytics system
- Dark mode

---

# 👨‍💻 Developer

**Rehan Solkar**

---

# 📄 License

This project is created for educational and academic purposes.

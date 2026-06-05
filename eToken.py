from flask import Flask, request, session, redirect, Response
import sqlite3
import random
import string
from datetime import datetime
import csv
from io import StringIO
import os

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

DB_NAME = "tokens.db"

# -------------------------
# ADMIN LOGIN
# -------------------------
ADMIN_USER = "admin"
ADMIN_PASS = "Cec@123"


# -------------------------
# DB INIT
# -------------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Mobile TEXT,
            UniqueCode TEXT,
            Evaluator TEXT,
            Token TEXT UNIQUE,
            DateTime TEXT,
            Status TEXT
        )
        """)

init_db()


# -------------------------
# TOKEN GENERATOR
# -------------------------
def generate_token():
    chars = string.ascii_uppercase + string.digits

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        while True:
            token = ''.join(random.choices(chars, k=6))
            c.execute("SELECT 1 FROM tokens WHERE Token=?", (token,))
            if not c.fetchone():
                return token


# -------------------------
# COMMON CSS
# -------------------------
STYLE = """
<style>
body{
    margin:0;
    font-family: 'Segoe UI', sans-serif;
    background:#f4f6fb;
}

/* TOP BAR */
.header{
    background:linear-gradient(135deg,#2a5298,#1e3c72);
    color:white;
    padding:18px;
    text-align:center;
    font-size:22px;
    font-weight:bold;
}

/* CENTER BOX */
.container{
    width:420px;
    margin:60px auto;
    background:white;
    padding:25px;
    border-radius:14px;
    box-shadow:0 10px 30px rgba(0,0,0,0.12);
}

/* INPUT */
input{
    width:100%;
    padding:12px;
    margin:10px 0;
    border:1px solid #ddd;
    border-radius:8px;
    outline:none;
}

input:focus{
    border-color:#2a5298;
}

/* BUTTON */
button{
    width:100%;
    padding:12px;
    background:#2a5298;
    color:white;
    border:none;
    border-radius:8px;
    font-weight:bold;
    cursor:pointer;
}

button:hover{
    background:#1e3c72;
}

/* LINKS */
a{
    color:#2a5298;
    text-decoration:none;
    font-weight:600;
}

/* DASHBOARD CARDS */
.cards{
    display:flex;
    justify-content:center;
    gap:15px;
    margin-top:30px;
}

.card{
    background:white;
    padding:20px;
    border-radius:12px;
    width:160px;
    text-align:center;
    box-shadow:0 6px 20px rgba(0,0,0,0.08);
}

.big{
    font-size:28px;
    font-weight:bold;
    color:#2a5298;
}

/* MENU */
.menu{
    text-align:center;
    margin-top:30px;
}

.menu a{
    display:inline-block;
    margin:8px;
    padding:10px 14px;
    background:#2a5298;
    color:white;
    border-radius:8px;
}
.menu a:hover{
    background:#1e3c72;
}
</style>
"""


# -------------------------
# HOME (USER)
# -------------------------
@app.route("/")
def home():
    return f"""
    <html>
    <head>{STYLE}</head>
    <body>

    <div class="header">Gate Entry System</div>

    <div class="container">

        <h3 style="text-align:center;">Generate Token</h3>

        <form action="/generate" method="post">

            <input name="mobile" placeholder="10 Digit Mobile" maxlength="10" required>
            <input name="code" placeholder="Unique Code" required>
            <input name="evaluator" placeholder="Evaluator Name" required>

            <button>Generate Token</button>

        </form>

        <p style="text-align:center;margin-top:15px;">
            <a href="/admin">Admin Login</a>
        </p>

    </div>

    </body>
    </html>
    """


# -------------------------
# GENERATE TOKEN
# -------------------------
@app.route("/generate", methods=["POST"])
def generate():

    mobile = request.form.get("mobile", "").strip()
    code = request.form.get("code", "").strip()
    evaluator = request.form.get("evaluator", "").strip()

    if not mobile.isdigit() or len(mobile) != 10:
        return "<h2>Invalid Mobile Number</h2>"

    token = generate_token()

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        INSERT INTO tokens
        (Mobile, UniqueCode, Evaluator, Token, DateTime, Status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mobile, code, evaluator,
            token,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "NOT USED"
        ))
        conn.commit()

    return f"""
    <html>
    <head>{STYLE}</head>
    <body>

    <div class="header">Token Generated</div>

    <div class="container" style="text-align:center;">

        <h2 style="color:#2a5298;">Your Token</h2>

        <div style="
            font-size:50px;
            font-weight:bold;
            color:green;
            margin:20px;">
            {token}
        </div>

        <a href="/">Generate Another</a>

    </div>

    </body>
    </html>
    """


# -------------------------
# ADMIN LOGIN
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":
        if request.form.get("user") == ADMIN_USER and request.form.get("pass") == ADMIN_PASS:
            session["admin"] = True
            return redirect("/dashboard")
        return "<h3>Invalid Login</h3>"

    return f"""
    <html>
    <head>{STYLE}</head>
    <body>

    <div class="header">Admin Login</div>

    <div class="container">

        <form method="post">

            <input name="user" placeholder="Username">
            <input name="pass" type="password" placeholder="Password">

            <button>Login</button>

        </form>

    </div>

    </body>
    </html>
    """


def admin_required():
    return session.get("admin") is True


# -------------------------
# DASHBOARD
# -------------------------
@app.route("/dashboard")
def dashboard():

    if not admin_required():
        return redirect("/admin")

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM tokens")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM tokens WHERE Status='USED'")
        used = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM tokens WHERE Status='NOT USED'")
        unused = c.fetchone()[0]

    return f"""
    <html>
    <head>{STYLE}</head>
    <body>

    <div class="header">Admin Dashboard</div>

    <div class="cards">

        <div class="card">
            <div>Total</div>
            <div class="big">{total}</div>
        </div>

        <div class="card">
            <div>Used</div>
            <div class="big">{used}</div>
        </div>

        <div class="card">
            <div>Unused</div>
            <div class="big">{unused}</div>
        </div>

    </div>

    <div class="menu">
        <a href="/verify">Verify</a>
        <a href="/data">Records</a>
        <a href="/export">CSV</a>
        <a href="/logout">Logout</a>
    </div>

    </body>
    </html>
    """


# -------------------------
# VERIFY
# -------------------------
@app.route("/verify")
def verify():

    if not admin_required():
        return redirect("/admin")

    return f"""
    <html>
    <head>{STYLE}</head>
    <body>

    <div class="header">Verify Token</div>

    <div class="container">

        <form action="/check" method="post">

            <input name="token" placeholder="Enter Token">
            <button>Verify</button>

        </form>

    </div>

    </body>
    </html>
    """


@app.route("/check", methods=["POST"])
def check():

    if not admin_required():
        return redirect("/admin")

    token = request.form.get("token", "").strip().upper()

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM tokens WHERE Token=?", (token,))
        row = c.fetchone()

        if not row:
            return "<h2>INVALID TOKEN</h2>"

        if row[6] == "USED":
            return "<h2>TOKEN ALREADY USED</h2>"

        c.execute("UPDATE tokens SET Status='USED' WHERE Token=?", (token,))
        conn.commit()

    return f"""
    <h2 style="color:green;text-align:center;">VALID TOKEN</h2>
    """


# -------------------------
# DATA
# -------------------------
@app.route("/data")
def data():

    if not admin_required():
        return redirect("/admin")

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM tokens ORDER BY id DESC")
        rows = c.fetchall()

    html = "<h2 style='text-align:center;'>Records</h2>"
    html += "<div style='width:90%;margin:auto;'>"
    html += "<table border='1' width='100%' cellpadding='8'>"
    html += "<tr><th>ID</th><th>Mobile</th><th>Code</th><th>Evaluator</th><th>Token</th><th>Date</th><th>Status</th></tr>"

    for r in rows:
        html += "<tr>" + "".join([f"<td>{x}</td>" for x in r]) + "</tr>"

    html += "</table></div>"
    return html


# -------------------------
# EXPORT
# -------------------------
@app.route("/export")
def export():

    if not admin_required():
        return redirect("/admin")

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM tokens")
        rows = c.fetchall()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","Mobile","Code","Evaluator","Token","Date","Status"])
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=records.csv"}
    )


# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")


# -------------------------
# RUN (RENDER READY)
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

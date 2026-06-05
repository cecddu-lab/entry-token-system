from flask import Flask, request, session, redirect, Response
import sqlite3
import random
import string
from datetime import datetime
import csv
from io import StringIO
import os

app = Flask(__name__)

# 🔐 Required for session (admin login)
app.secret_key = "CHANGE_THIS_TO_RANDOM_SECRET"

DB_NAME = "tokens.db"

# -------------------------
# ADMIN LOGIN
# -------------------------
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"


# -------------------------
# INIT DB
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
# USER PAGE (ONLY GENERATE)
# -------------------------
@app.route("/")
def home():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:60px;">

        <h2>Gate Entry System</h2>

        <form action="/generate" method="post">

            <input name="mobile" placeholder="10 Digit Mobile"
                maxlength="10" required><br><br>

            <input name="code" placeholder="Unique Code" required><br><br>

            <input name="evaluator" placeholder="Evaluator Name" required><br><br>

            <button>Generate Token</button>

        </form>

        <br><br>
        <a href="/admin">Admin Login</a>

    </body>
    </html>
    """


# -------------------------
# GENERATE TOKEN (USER)
# -------------------------
@app.route("/generate", methods=["POST"])
def generate():

    mobile = request.form.get("mobile", "").strip()
    code = request.form.get("code", "").strip()
    evaluator = request.form.get("evaluator", "").strip()

    # 10-digit validation
    if not mobile.isdigit() or len(mobile) != 10:
        return "<h2>Mobile must be exactly 10 digits</h2>"

    token = generate_token()

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        INSERT INTO tokens
        (Mobile, UniqueCode, Evaluator, Token, DateTime, Status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mobile,
            code,
            evaluator,
            token,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "NOT USED"
        ))
        conn.commit()

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">

        <h2>Token Generated</h2>

        <h1 style="color:green;font-size:50px;">
            {token}
        </h1>

        <a href="/">Back</a>

    </body>
    </html>
    """


# -------------------------
# ADMIN LOGIN
# -------------------------
@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":
        u = request.form.get("user")
        p = request.form.get("pass")

        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin"] = True
            return redirect("/dashboard")

        return "<h3>Invalid Login</h3>"

    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:100px;">

        <h2>Admin Login</h2>

        <form method="post">
            <input name="user" placeholder="Username"><br><br>
            <input name="pass" type="password" placeholder="Password"><br><br>
            <button>Login</button>
        </form>

    </body>
    </html>
    """


# -------------------------
# CHECK ADMIN
# -------------------------
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
    <body style="font-family:Arial;padding:30px;">

        <h1>Admin Dashboard</h1>

        <h3>Total Tokens: {total}</h3>
        <h3>Used: {used}</h3>
        <h3>Unused: {unused}</h3>

        <br>

        <a href="/verify">Verify Token</a><br><br>
        <a href="/data">View Data</a><br><br>
        <a href="/export">Export CSV</a><br><br>
        <a href="/logout">Logout</a>

    </body>
    </html>
    """


# -------------------------
# VERIFY (ADMIN ONLY)
# -------------------------
@app.route("/verify")
def verify():

    if not admin_required():
        return redirect("/admin")

    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">

        <h2>Verify Token</h2>

        <form action="/check" method="post">

            <input name="token" placeholder="Enter Token"><br><br>
            <button>Verify</button>

        </form>

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
    <h2 style="color:green;">VALID TOKEN</h2>
    <p>Mobile: {row[1]}</p>
    <p>Code: {row[2]}</p>
    <p>Evaluator: {row[3]}</p>
    <p>Token: {row[4]}</p>
    """


# -------------------------
# VIEW DATA
# -------------------------
@app.route("/data")
def data():

    if not admin_required():
        return redirect("/admin")

    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM tokens ORDER BY id DESC")
        rows = c.fetchall()

    html = """
    <h2>All Records</h2>
    <table border="1" cellpadding="5">
    <tr>
        <th>ID</th><th>Mobile</th><th>Code</th>
        <th>Evaluator</th><th>Token</th>
        <th>Date</th><th>Status</th>
    </tr>
    """

    for r in rows:
        html += "<tr>" + "".join([f"<td>{x}</td>" for x in r]) + "</tr>"

    html += "</table><br><a href='/dashboard'>Back</a>"
    return html


# -------------------------
# EXPORT CSV
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
# RENDER ENTRY POINT FIX
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )

from flask import Flask, request, render_template_string
import random
import string
from datetime import datetime
import sqlite3

app = Flask(__name__)

DB_NAME = "tokens.db"


# -----------------------------
# INIT DATABASE
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Mobile TEXT,
            UniqueCode TEXT,
            EvaluatorName TEXT,
            Token TEXT UNIQUE,
            DateTime TEXT,
            Status TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# -----------------------------
# TOKEN GENERATOR
# -----------------------------
def generate_token():
    chars = string.ascii_uppercase + string.digits

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    while True:
        token = ''.join(random.choices(chars, k=4))

        c.execute("SELECT Token FROM tokens WHERE Token=?", (token,))
        if not c.fetchone():
            conn.close()
            return token


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    html = """
    <html>
    <head>
    <title>Entry System</title>
    <style>
    body{
        font-family: Arial;
        background: linear-gradient(120deg, #1e3c72, #2a5298);
        margin:0;
        padding:0;
    }
    .container{
        width: 420px;
        margin: 80px auto;
        background: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    h2{text-align:center;color:#2a5298;}
    input{
        width: 100%;
        padding: 12px;
        margin: 8px 0;
        border: 1px solid #ccc;
        border-radius: 8px;
    }
    button{
        width: 100%;
        padding: 12px;
        background: #2a5298;
        color: white;
        border: none;
        border-radius: 8px;
        cursor: pointer;
    }
    button:hover{background:#1e3c72;}
    a{
        display:block;
        text-align:center;
        margin-top:15px;
        color:#2a5298;
        text-decoration:none;
        font-weight:bold;
    }
    </style>
    </head>
    <body>

    <div class="container">
    <h2>Gate Entry System</h2>

    <form action="/generate" method="post">
        <input name="mobile" placeholder="Mobile Number" required>
        <input name="unique_code" placeholder="Unique Code" required>
        <input name="evaluator" placeholder="Evaluator Name" required>
        <button type="submit">Generate Token</button>
    </form>

    <a href="/verify">Go to Verification Panel</a>
    </div>

    </body>
    </html>
    """
    return render_template_string(html)


# -----------------------------
# GENERATE TOKEN
# -----------------------------
@app.route("/generate", methods=["POST"])
def generate():
    try:
        mobile = request.form["mobile"]
        unique_code = request.form["unique_code"]
        evaluator = request.form["evaluator"]

        token = generate_token()

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("""
            INSERT INTO tokens (Mobile, UniqueCode, EvaluatorName, Token, DateTime, Status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            mobile,
            unique_code,
            evaluator,
            token,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "NOT USED"
        ))

        conn.commit()
        conn.close()

        return f"""
        <html>
        <body style="font-family:Arial;text-align:center;margin-top:80px;">
        <h2>ENTRY SUCCESSFUL</h2>
        <h1 style="color:green;font-size:60px;">{token}</h1>
        <p><b>Evaluator:</b> {evaluator}</p>
        <a href="/">Generate Another</a>
        </body>
        </html>
        """

    except Exception as e:
        print("ERROR:", e)
        return "<h2>Internal Server Error</h2>"


# -----------------------------
# VERIFY PAGE
# -----------------------------
@app.route("/verify")
def verify():
    html = """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
    <h2>Verify Token</h2>

    <form action="/check" method="post">
        <input name="token" placeholder="Enter Token" required>
        <button type="submit">Verify</button>
    </form>

    </body>
    </html>
    """
    return html


# -----------------------------
# CHECK TOKEN
# -----------------------------
@app.route("/check", methods=["POST"])
def check():

    token = request.form["token"]

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM tokens WHERE Token=?", (token,))
    record = c.fetchone()

    if not record:
        return "<h2>INVALID TOKEN</h2>"

    c.execute("UPDATE tokens SET Status='USED' WHERE Token=?", (token,))
    conn.commit()
    conn.close()

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">
    <h1 style="color:green;">VALID TOKEN</h1>

    <p><b>Mobile:</b> {record[1]}</p>
    <p><b>Code:</b> {record[2]}</p>
    <p><b>Evaluator:</b> {record[3]}</p>
    <p><b>Token:</b> {record[4]}</p>
    <p><b>Status:</b> USED</p>

    <a href="/verify">Verify Another</a>
    </body>
    </html>
    """


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

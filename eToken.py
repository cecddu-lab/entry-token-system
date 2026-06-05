from flask import Flask, request, render_template_string, Response
import random
import string
from datetime import datetime
import sqlite3
import csv
from io import StringIO
import os

app = Flask(__name__)

DB_NAME = "tokens.db"


# -----------------------------
# DATABASE INITIALIZATION
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

        c.execute(
            "SELECT Token FROM tokens WHERE Token=?",
            (token,)
        )

        if not c.fetchone():
            conn.close()
            return token


# -----------------------------
# HOME PAGE
# -----------------------------
@app.route("/")
def home():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Gate Entry System</title>
        <style>
            body{
                font-family:Arial;
                background:linear-gradient(120deg,#1e3c72,#2a5298);
                margin:0;
                padding:0;
            }

            .container{
                width:420px;
                margin:80px auto;
                background:white;
                padding:25px;
                border-radius:15px;
                box-shadow:0 10px 30px rgba(0,0,0,0.3);
            }

            h2{
                text-align:center;
                color:#2a5298;
            }

            input{
                width:100%;
                padding:12px;
                margin:8px 0;
                border:1px solid #ccc;
                border-radius:8px;
                box-sizing:border-box;
            }

            button{
                width:100%;
                padding:12px;
                background:#2a5298;
                color:white;
                border:none;
                border-radius:8px;
                cursor:pointer;
            }

            button:hover{
                background:#1e3c72;
            }

            .links a{
                display:block;
                margin-top:12px;
                text-align:center;
                text-decoration:none;
                font-weight:bold;
                color:#2a5298;
            }
        </style>
    </head>
    <body>

        <div class="container">

            <h2>Gate Entry System</h2>

            <form action="/generate" method="post">

                <input name="mobile"
                       placeholder="Mobile Number"
                       required>

                <input name="unique_code"
                       placeholder="Unique Code"
                       required>

                <input name="evaluator"
                       placeholder="Evaluator Name"
                       required>

                <button type="submit">
                    Generate Token
                </button>

            </form>

            <div class="links">
                <a href="/verify">Verification Panel</a>
                <a href="/data">View Data</a>
                <a href="/export">Download CSV</a>
            </div>

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
        mobile = request.form.get("mobile", "").strip()
        unique_code = request.form.get("unique_code", "").strip()
        evaluator = request.form.get("evaluator", "").strip()

        token = generate_token()

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute("""
            INSERT INTO tokens
            (
                Mobile,
                UniqueCode,
                EvaluatorName,
                Token,
                DateTime,
                Status
            )
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

            <div style="
                font-size:60px;
                color:green;
                font-weight:bold;
                letter-spacing:5px;">
                {token}
            </div>

            <p><b>Evaluator:</b> {evaluator}</p>

            <a href="/">Generate Another</a>

        </body>
        </html>
        """

    except Exception as e:
        print("ERROR:", e)
        return f"<h2>Internal Server Error</h2><p>{str(e)}</p>", 500


# -----------------------------
# VERIFY PAGE
# -----------------------------
@app.route("/verify")
def verify():
    return """
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">

        <h2>Verify Token</h2>

        <form action="/check" method="post">

            <input
                name="token"
                placeholder="Enter Token"
                required
                style="padding:12px;width:250px;">

            <br><br>

            <button style="padding:12px 20px;">
                Verify
            </button>

        </form>

    </body>
    </html>
    """


# -----------------------------
# CHECK TOKEN
# -----------------------------
@app.route("/check", methods=["POST"])
def check():
    token = request.form.get("token", "").strip()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT * FROM tokens WHERE Token=?",
        (token,)
    )

    record = c.fetchone()

    if not record:
        conn.close()
        return "<h2>INVALID TOKEN</h2>"

    c.execute(
        "UPDATE tokens SET Status='USED' WHERE Token=?",
        (token,)
    )

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
# VIEW DATA
# -----------------------------
@app.route("/data")
def view_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
        SELECT Mobile,
               UniqueCode,
               EvaluatorName,
               Token,
               DateTime,
               Status
        FROM tokens
        ORDER BY id DESC
    """)

    rows = c.fetchall()
    conn.close()

    html = """
    <html>
    <head>
    <title>Stored Records</title>
    <style>
        table{
            border-collapse:collapse;
            width:100%;
        }

        th,td{
            border:1px solid #ccc;
            padding:8px;
            text-align:left;
        }

        th{
            background:#2a5298;
            color:white;
        }
    </style>
    </head>
    <body>

    <h2>Stored Records</h2>

    <table>
        <tr>
            <th>Mobile</th>
            <th>Code</th>
            <th>Evaluator</th>
            <th>Token</th>
            <th>Date Time</th>
            <th>Status</th>
        </tr>
    """

    for row in rows:
        html += f"""
        <tr>
            <td>{row[0]}</td>
            <td>{row[1]}</td>
            <td>{row[2]}</td>
            <td>{row[3]}</td>
            <td>{row[4]}</td>
            <td>{row[5]}</td>
        </tr>
        """

    html += """
    </table>

    <br>
    <a href="/">Back Home</a>

    </body>
    </html>
    """

    return html


# -----------------------------
# EXPORT CSV
# -----------------------------
@app.route("/export")
def export_csv():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM tokens")
    rows = c.fetchall()

    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Mobile",
        "UniqueCode",
        "EvaluatorName",
        "Token",
        "DateTime",
        "Status"
    ])

    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=tokens.csv"
        }
    )


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/health")
def health():
    return "OK"


# -----------------------------
# RUN APP
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

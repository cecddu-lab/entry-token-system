from flask import Flask, request, session, redirect, Response
import sqlite3
import secrets
import string
import os
import csv
import io
import base64
from datetime import datetime
from markupsafe import escape

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,  # Set to False if testing locally without HTTPS
    SESSION_COOKIE_SAMESITE='Lax',
)

DB_NAME = "tokens.db"
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")

def db():
    return sqlite3.connect(DB_NAME)

def init_db():
    with db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            UniqueCode TEXT NOT NULL,
            Evaluator TEXT NOT NULL,
            Token TEXT UNIQUE NOT NULL,
            DateTime TEXT NOT NULL,
            Status TEXT DEFAULT 'NOT USED'
        )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens(Token);")
init_db()

def generate_token():
    chars = string.ascii_uppercase + string.digits
    while True:
        t = ''.join(secrets.choice(chars) for _ in range(6))
        with db() as conn:
            if not conn.execute("SELECT 1 FROM tokens WHERE Token=?", (t,)).fetchone():
                return t

def qr_base64(text):
    try:
        import qrcode
        buf = io.BytesIO()
        qrcode.make(text).save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None

STYLE = """
<style>
body{font-family:Arial, sans-serif;background:#f4f6fb;margin:0}
.header{background:#1e3c72;color:white;padding:16px;text-align:center}
.box{max-width:700px;margin:20px auto;background:white;padding:20px;border-radius:10px;box-shadow: 0 4px 6px rgba(0,0,0,0.1)}
input,button,select{padding:10px;width:100%;margin:5px 0;box-sizing:border-box}
button{background:#1e3c72;color:white;border:none;cursor:pointer;font-weight:bold}
button:hover{background:#152b52}
table{width:100%;border-collapse:collapse;margin-top:15px}
td,th{border:1px solid #ddd;padding:8px;text-align:left}
th{background-color:#1e3c72;color:white}
tr:nth-child(even){background-color: #f2f2f2}
a{margin-right:15px;color:#1e3c72;text-decoration:none;font-weight:bold}
a:hover{text-decoration:underline}
</style>
"""

def admin_required():
    return session.get("admin") is True

@app.route("/")
def home():
    return f"""
    <html><head>{STYLE}</head><body>
    <div class='header'><h1>Gate Entry QR Token System</h1></div>
    <div class='box'>
    <form method='post' action='/generate'>
    <input name='code' placeholder='Unique Code' required>
    <input name='evaluator' placeholder='Evaluator Name' required>
    <button type="submit">Generate Token</button>
    </form>
    <hr style="border:0;border-top:1px solid #eee;margin:20px 0;">
    <a href='/admin'>Admin Login</a>
    </div></body></html>
    """

@app.route("/generate", methods=["POST"])
def generate():
    code = request.form.get("code", "").strip()
    evaluator = request.form.get("evaluator", "").strip()

    if not code or not evaluator:
        return "<h3>Missing required fields.</h3>", 400

    token = generate_token()

    with db() as conn:
        cursor = conn.execute("""INSERT INTO tokens
        (UniqueCode,Evaluator,Token,DateTime,Status)
        VALUES(?,?,?,?,?)""",
        (code, evaluator, token,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         "NOT USED"))
        # Get the auto-incremented Serial Number (ID) of the row just inserted
        serial_no = cursor.lastrowid

    # Combine Serial Number and Token string directly into the QR payload
    qr_payload = f"S.No: {serial_no} | Token: {token}"
    qr = qr_base64(qr_payload)
    img = f"<img width='250' src='data:image/png;base64,{qr}' alt='QR Code'>" if qr else "<p>(QR generation failed)</p>"

    return f"""
    <html><head>{STYLE}</head><body>
    <div class='box' style='text-align:center'>
    <p>Your Token Details (Token No: {serial_no}):</p>
    <h1 style="font-size:3rem; margin:10px 0; color:#1e3c72;">{escape(token)}</h1>
    {img}
    <p style="margin-top:15px; color:#555;">Show this QR / Token string at the CEC security gate.</p>
    <a href='/'>← Back to Home</a>
    </div></body></html>
    """

@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form.get("user") == ADMIN_USER and request.form.get("pass") == ADMIN_PASS:
            session["admin"] = True
            return redirect("/dashboard")
        return "<h3>Invalid Username or Password</h3>", 401

    return f"""
    <html><head>{STYLE}</head><body>
    <div class='box'>
    <h2>Admin Portal Login</h2>
    <form method='post'>
    <input name='user' placeholder='Username' required>
    <input type='password' name='pass' placeholder='Password' required>
    <button type="submit">Login</button>
    </form>
    <a href='/'>← Home</a>
    </div></body></html>
    """

@app.route("/dashboard")
def dashboard():
    if not admin_required(): return redirect("/admin")
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
        used = conn.execute("SELECT COUNT(*) FROM tokens WHERE Status='USED'").fetchone()[0]
        unused = conn.execute("SELECT COUNT(*) FROM tokens WHERE Status='NOT USED'").fetchone()[0]

    return f"""
    <html><head>{STYLE}</head><body>
    <div class='header'><h1>Admin Dashboard</h1></div>
    <div class='box'>
    <div style="display:flex; justify-content:space-around; margin-bottom:20px; background:#f4f6fb; padding:15px; border-radius:5px;">
        <div><strong>Total Tokens:</strong> {total}</div>
        <div style="color:green"><strong>Used:</strong> {used}</div>
        <div style="color:orange"><strong>Unused:</strong> {unused}</div>
    </div>
    <div style="text-align:center;">
        <a href='/verify'>✓ Scan/Verify Token</a>
        <a href='/data'>📋 View Records</a>
        <a href='/export'>📥 Export CSV</a>
        <a href='/logout' style="color:#cc0000">Logout</a>
    </div>
    </div></body></html>
    """

@app.route("/verify")
def verify():
    if not admin_required(): return redirect("/admin")
    return f"""
    <html><head>{STYLE}</head><body>
    <div class='box'>
    <h2>Gate Verification</h2>
    <form method='post' action='/check'>
    <input name='token' placeholder='Enter Token or Scan QR' autofocus required autocomplete="off">
    <button type="submit">Verify & Check-In</button>
    </form>
    <p style="color:#666; font-size:0.9rem;">💡 Note: If scanning a QR code containing a Serial Number, the system automatically isolates the unique token identifier string.</p>
    <br><a href='/dashboard'>← Dashboard</a>
    </div></body></html>
    """

@app.route("/check", methods=["POST"])
def check():
    if not admin_required(): return redirect("/admin")
    raw_input = request.form.get("token", "").upper().strip()
    
    # Smart parsing: if QR scanner reads the full string payload "S.No: X | Token: YYYYYY", 
    # extract just the token part. Otherwise, use the raw string directly.
    token = raw_input
    if "TOKEN:" in raw_input:
        try:
            token = raw_input.split("TOKEN:")[-1].strip()
        except Exception:
            pass

    with db() as conn:
        row = conn.execute("SELECT Status FROM tokens WHERE Token=?", (token,)).fetchone()
        if not row: 
            color, msg = "red", "INVALID TOKEN"
        elif row[0] == "USED": 
            color, msg = "orange", "TOKEN ALREADY USED"
        else:
            conn.execute("UPDATE tokens SET Status='USED' WHERE Token=?", (token,))
            color, msg = "green", "VALID TOKEN - ACCESS GRANTED"

    return f"""
    <html><head>{STYLE}</head><body>
    <div class='box' style='text-align:center; padding:40px 20px;'>
    <h1 style='color:{color}; font-size:2.5rem;'>{msg}</h1>
    <br><br>
    <a href='/verify' style='background:#1e3c72; color:white; padding:10px 20px; border-radius:5px;'>Scan Another</a>
    <a href='/dashboard'>Dashboard</a>
    </div></body></html>
    """

@app.route("/data")
def data():
    if not admin_required(): return redirect("/admin")
    q = request.args.get("q", "").strip()

    with db() as conn:
        if q:
            rows = conn.execute("SELECT * FROM tokens WHERE Token LIKE ? ORDER BY id DESC", (f"%{q}%",)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM tokens ORDER BY id DESC").fetchall()

    html = f"""<html><head>{STYLE}</head><body><div class='box'>
    <h2>Token Logs</h2>
    <a href='/dashboard'>← Dashboard</a><br><br>
    <form method='get'><input name='q' value='{escape(q)}' placeholder='Search by Token...'></form>
    <table>
    <tr><th>Serial No (ID)</th><th>Code</th><th>Evaluator</th><th>Token</th><th>Date</th><th>Status</th></tr>"""
    
    for r in rows:
        html += "<tr>" + "".join(f"<td>{escape(str(x))}</td>" for x in r) + "</tr>"
        
    html += "</table></div></body></html>"
    return html

@app.route("/export")
def export():
    if not admin_required(): return redirect("/admin")
    out = io.StringIO()
    w = csv.writer(out)

    with db() as conn:
        rows = conn.execute("SELECT * FROM tokens").fetchall()

    w.writerow(["Serial No (ID)", "Code", "Evaluator", "Token", "Date", "Status"])
    w.writerows(rows)

    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=gate_records.csv"}
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

from flask import Flask, request, render_template_string
import pandas as pd
import random
import string
from datetime import datetime
import os

app = Flask(__name__)

FILE_NAME = "tokens.xlsx"


# -----------------------------
# TOKEN GENERATOR
# -----------------------------
def generate_token():

    chars = string.ascii_uppercase + string.digits

    while True:

        token = ''.join(random.choices(chars, k=4))

        if os.path.exists(FILE_NAME):

            df = pd.read_excel(FILE_NAME)

            if token not in df["Token"].astype(str).values:
                return token
        else:
            return token


# -----------------------------
# HOME PAGE (STYLED)
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

    h2{
        text-align:center;
        color:#2a5298;
    }

    input{
        width: 100%;
        padding: 12px;
        margin: 8px 0;
        border: 1px solid #ccc;
        border-radius: 8px;
        font-size: 14px;
    }

    button{
        width: 100%;
        padding: 12px;
        background: #2a5298;
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        cursor: pointer;
        transition: 0.3s;
    }

    button:hover{
        background: #1e3c72;
    }

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

    mobile = request.form["mobile"]
    unique_code = request.form["unique_code"]
    evaluator = request.form["evaluator"]

    token = generate_token()

    row = pd.DataFrame([{
        "Mobile": mobile,
        "UniqueCode": unique_code,
        "EvaluatorName": evaluator,
        "Token": token,
        "DateTime": datetime.now(),
        "Status": "NOT USED"
    }])

    if os.path.exists(FILE_NAME):

        df = pd.read_excel(FILE_NAME)
        df = pd.concat([df, row], ignore_index=True)

    else:
        df = row

    df.to_excel(FILE_NAME, index=False)

    html = f"""
    <html>
    <head>
    <style>
    body {{
        font-family: Arial;
        background: #f4f6f9;
        text-align:center;
        padding-top:80px;
    }}

    .card {{
        background:white;
        display:inline-block;
        padding:40px;
        border-radius:15px;
        box-shadow:0 10px 25px rgba(0,0,0,0.2);
    }}

    .token {{
        font-size:60px;
        color:green;
        font-weight:bold;
        letter-spacing:5px;
    }}

    a {{
        display:block;
        margin-top:20px;
        text-decoration:none;
        color:#2a5298;
        font-weight:bold;
    }}
    </style>
    </head>

    <body>

    <div class="card">

    <h2>ENTRY SUCCESSFUL</h2>

    <div class="token">{token}</div>

    <p><b>Evaluator:</b> {evaluator}</p>

    <a href="/">Generate Another</a>

    </div>

    </body>
    </html>
    """

    return html


# -----------------------------
# VERIFY PAGE (STYLED)
# -----------------------------
@app.route("/verify")
def verify():

    html = """
    <html>
    <head>
    <style>

    body{
        font-family:Arial;
        background:linear-gradient(120deg,#2a5298,#1e3c72);
        margin:0;
    }

    .box{
        width:400px;
        margin:100px auto;
        background:white;
        padding:25px;
        border-radius:15px;
        text-align:center;
    }

    input{
        width:100%;
        padding:12px;
        margin:10px 0;
        border-radius:8px;
        border:1px solid #ccc;
    }

    button{
        width:100%;
        padding:12px;
        background:#1e3c72;
        color:white;
        border:none;
        border-radius:8px;
        font-size:16px;
    }

    </style>
    </head>

    <body>

    <div class="box">

    <h2>Verify Token</h2>

    <form action="/check" method="post">

        <input name="token" placeholder="Enter Token" required>

        <button type="submit">Verify</button>

    </form>

    </div>

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

    if not os.path.exists(FILE_NAME):
        return "<h2>INVALID TOKEN</h2>"

    df = pd.read_excel(FILE_NAME)

    match = df[df["Token"].astype(str) == token]

    if len(match) == 0:
        return "<h2>INVALID TOKEN</h2>"

    record = match.iloc[0]

    df.loc[df["Token"] == token, "Status"] = "USED"
    df.to_excel(FILE_NAME, index=False)

    return f"""
    <html>
    <body style="font-family:Arial;text-align:center;margin-top:80px;">

    <h1 style="color:green;">VALID TOKEN</h1>

    <p><b>Mobile:</b> {record['Mobile']}</p>
    <p><b>Code:</b> {record['UniqueCode']}</p>
    <p><b>Evaluator:</b> {record['EvaluatorName']}</p>
    <p><b>Status:</b> USED</p>

    <br>
    <a href="/verify">Verify Another</a>

    </body>
    </html>
    """


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    

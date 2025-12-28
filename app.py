# FINAL STEP – COMPLETE MULTI-USER EMAIL BIRTHDAY WISHER
# (With Login, Signup, OTP, Per‑User Gmail App Password)

# ================= app.py =================
from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, os, random, hashlib
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# ================= DATABASES =================
USERS_DB = 'users.db'
OTP_DB = 'otp.db'
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# ================= UTILITIES =================
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# ================= INIT DB =================
def init_dbs():
    with sqlite3.connect(USERS_DB) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            app_password TEXT,
            login_password TEXT
        )''')

    with sqlite3.connect(OTP_DB) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS otp(
            email TEXT,
            code TEXT,
            expiry DATETIME
        )''')

init_dbs()

# ================= EMAIL =================
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# ================= AUTH =================
@app.route('/', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email=request.form['email']
        pwd=hash_password(request.form['password'])
        with sqlite3.connect(USERS_DB) as con:
            u=con.execute('SELECT * FROM users WHERE email=? AND login_password=?',(email,pwd)).fetchone()
        if not u:
            return render_template('login.html',error='Invalid credentials')
        session['uid']=u[0]
        session['email']=u[1]
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method=='POST':
        email=request.form['email']
        otp=str(random.randint(100000,999999))
        exp=datetime.now()+timedelta(minutes=5)
        with sqlite3.connect(OTP_DB) as con:
            con.execute('INSERT INTO otp VALUES(?,?,?)',(email,otp,exp))

        server=smtplib.SMTP(SMTP_SERVER,SMTP_PORT)
        server.starttls()
        server.login(email,request.form['temp_pass'])
        server.sendmail(email,email,f"Your OTP is {otp}")
        server.quit()
        session['tmp_email']=email
        return redirect('/verify')
    return render_template('signup.html')

@app.route('/verify',methods=['GET','POST'])
def verify():
    if request.method=='POST':
        otp=request.form['otp']
        email=session['tmp_email']
        with sqlite3.connect(OTP_DB) as con:
            row=con.execute('SELECT * FROM otp WHERE email=? AND code=?',(email,otp)).fetchone()
        if not row:
            return render_template('verify.html',error='Invalid OTP')
        return redirect('/setpass')
    return render_template('verify.html')

@app.route('/setpass',methods=['GET','POST'])
def setpass():
    if request.method=='POST':
        with sqlite3.connect(USERS_DB) as con:
            con.execute('INSERT INTO users(email,app_password,login_password) VALUES(?,?,?)',(
                session['tmp_email'],
                request.form['app'],
                hash_password(request.form['password'])
            ))
        return redirect('/')
    return render_template('setpass.html')

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    uid=session['uid']
    db=f"{DATA_DIR}/user_{uid}.db"
    con=sqlite3.connect(db)
    con.execute('''CREATE TABLE IF NOT EXISTS birthdays(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,email TEXT,day INT,month INT,gender TEXT
    )''')
    rows=con.execute('SELECT * FROM birthdays').fetchall()
    return render_template('index.html',birthdays=rows)

@app.route('/add',methods=['POST'])
def add():
    db=f"{DATA_DIR}/user_{session['uid']}.db"
    with sqlite3.connect(db) as con:
        con.execute('INSERT INTO birthdays(name,email,day,month,gender) VALUES(?,?,?,?,?)',tuple(request.form.values()))
    return redirect('/dashboard')

@app.route('/today')
def today():
    now=datetime.now()
    db=f"{DATA_DIR}/user_{session['uid']}.db"
    with sqlite3.connect(db) as con:
        rows=con.execute('SELECT * FROM birthdays WHERE day=? AND month=?',(now.day,now.month)).fetchall()
    return render_template('today.html',birthdays=rows)

@app.route('/send',methods=['POST'])
def send():
    with sqlite3.connect(USERS_DB) as con:
        u=con.execute('SELECT * FROM users WHERE id=?',(session['uid'],)).fetchone()

    server=smtplib.SMTP(SMTP_SERVER,SMTP_PORT)
    server.starttls()
    server.login(u[1],u[2])

    for p in request.json['selected']:
        msg=MIMEMultipart('alternative')
        msg['From']=u[1]
        msg['To']=p['email']
        msg['Subject']='Happy Birthday 🎉'
        msg.attach(MIMEText(f"<h2>Happy Birthday {p['name']} 🎂</h2>",'html'))
        server.send_message(msg)

    server.quit()
    return jsonify({'status':'sent'})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
({'status':'sent'})


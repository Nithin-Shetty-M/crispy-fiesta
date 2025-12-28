# FINAL MULTI-USER EMAIL BIRTHDAY WISHER WITH SIGNUP AND OTP

from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import sqlite3, os, hashlib, random, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'super-secret-key'

# DATABASES
USERS_DB = 'users.db'
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)
OTP_STORE = {}

# UTILITIES
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# SMTP CONFIG (GLOBAL)
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

def send_otp(email, otp):
    # Replace with your SMTP email server credentials for sending OTP

    SENDER_EMAIL = 'your_sender_email@gmail.com'
    SENDER_PASSWORD = 'your_sender_app_password'

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = email
    msg['Subject'] = 'Your OTP for Birthday Wisher'
    msg.attach(MIMEText(f'Your OTP is {otp}', 'plain'))

    server.send_message(msg)
    server.quit()

# INIT USERS DB
with sqlite3.connect(USERS_DB) as con:
    con.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        app_password TEXT,
        login_password TEXT
    )''')

# SIGNUP
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        email=request.form['email']
        otp=random.randint(100000,999999)
        OTP_STORE[email]=otp
        send_otp(email, otp)
        session['signup_email']=email
        return render_template('verify_otp.html', email=email)
    return render_template('signup.html')

# VERIFY OTP
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    email=session.get('signup_email')
    entered=request.form['otp']
    if email and OTP_STORE.get(email)==int(entered):
        return render_template('set_password.html', email=email)
    return render_template('verify_otp.html', email=email, error='Incorrect OTP')

# SET APP PASSWORD AND LOGIN PASSWORD
@app.route('/set_password', methods=['POST'])
def set_password():
    email=session.get('signup_email')
    app_password=request.form['app_password']
    login_password=hash_password(request.form['login_password'])

    with sqlite3.connect(USERS_DB) as con:
        con.execute('INSERT INTO users(email, app_password, login_password) VALUES(?,?,?)',
                    (email, app_password, login_password))
    session.pop('signup_email', None)
    return redirect(url_for('login'))

# LOGIN
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
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'uid' not in session:
        return redirect(url_for('login'))
    uid=session['uid']
    db=f"{DATA_DIR}/user_{uid}.db"
    with sqlite3.connect(db) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS birthdays(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,email TEXT,day INT,month INT,gender TEXT
        )''')
        rows=con.execute('SELECT * FROM birthdays').fetchall()
    return render_template('index.html',birthdays=rows)

# ADD, DELETE, TODAY, SEND EMAIL routes same as before (re-use previous logic)
# ADD BIRTHDAY
@app.route('/add',methods=['POST'])
def add():
    db=f"{DATA_DIR}/user_{session['uid']}.db"
    with sqlite3.connect(db) as con:
        con.execute('INSERT INTO birthdays(name,email,day,month,gender) VALUES(?,?,?,?,?)',tuple(request.form.values()))
    return redirect(url_for('dashboard'))

# TODAY BIRTHDAYS
@app.route('/today')
def today():
    now=datetime.now()
    db=f"{DATA_DIR}/user_{session['uid']}.db"
    with sqlite3.connect(db) as con:
        rows=con.execute('SELECT * FROM birthdays WHERE day=? AND month=?',(now.day,now.month)).fetchall()
    return render_template('today.html',birthdays=rows)

# SEND EMAIL
@app.route('/send',methods=['POST'])
def send():
    with sqlite3.connect(USERS_DB) as con:
        u=con.execute('SELECT * FROM users WHERE id=?',(session['uid'],)).fetchone()

    selected=request.json.get('selected', [])
    if not selected:
        return jsonify({'status':'no_birthdays'})

    server=smtplib.SMTP(SMTP_SERVER,SMTP_PORT)
    server.starttls()
    server.login(u[1],u[2])

    for p in selected:
        msg=MIMEMultipart('alternative')
        msg['From']=u[1]
        msg['To']=p['email']
        msg['Subject']='Happy Birthday 🎉'
        html_content=f"""
        <html>
          <body style='font-family:Arial;'>
            <h2>Happy Birthday {p['name']} 🎂</h2>
            <p>Wishing you a fantastic day and an amazing year ahead!</p>
          </body>
        </html>
        """
        msg.attach(MIMEText(html_content,'html'))
        server.send_message(msg)

    server.quit()
    return jsonify({'status':'sent'})

# DELETE BIRTHDAY SAFELY
@app.route('/delete/<int:id>')
def delete(id):
    if 'uid' not in session:
        return redirect(url_for('login'))
    db=f"{DATA_DIR}/user_{session['uid']}.db"

    # Ensure connection is fully closed after deletion
    remaining=0
    try:
        con=sqlite3.connect(db)
        con.execute('DELETE FROM birthdays WHERE id=?',(id,))
        con.commit()
        remaining=con.execute('SELECT COUNT(*) FROM birthdays').fetchone()[0]
    finally:
        con.close()

    # Remove database if empty
    if remaining==0 and os.path.exists(db):
        try:
            os.remove(db)
        except PermissionError:
            pass  # Ignore if still in use, will be removed later
    return redirect(url_for('dashboard'))

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__=='__main__':
    app.run(debug=True)




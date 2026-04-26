import sqlite3
import hashlib
import random
import smtplib
import os
from dotenv import load_dotenv
load_dotenv("bankprivacy.env")


from datetime import datetime
from email.mime.text import MIMEText
from flask import Flask, request, redirect, session, render_template
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
Talisman(app, content_security_policy=None, force_https=False)

# ==============================
# DATABASE CONNECTION
# ==============================
conn = sqlite3.connect("bankaccount.db" , check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

# ==============================
# TABLE CREATION
# ==============================

# 🔥 ACCOUNTS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS accounts(
    account_number TEXT PRIMARY KEY,
    cif_number TEXT UNIQUE,

    first_name TEXT NOT NULL,
    last_name TEXT,
    father_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    address TEXT NOT NULL,

    email TEXT UNIQUE NOT NULL,
    mobile TEXT UNIQUE NOT NULL,

    nominee_name TEXT NOT NULL,
    nominee_relation TEXT NOT NULL,
    nominee_mobile TEXT NOT NULL,

    account_type TEXT NOT NULL 
    CHECK(account_type IN ('Savings','Current')),

    balance REAL DEFAULT 0 CHECK(balance >= 0),

    mpin TEXT NOT NULL,

    account_creation_date TEXT,

    login_attempts INTEGER DEFAULT 0,
    lock_until TEXT,

    account_status TEXT DEFAULT 'Active'
    CHECK(account_status IN ('Active','Locked','Closed','Pending')),

    mpin_change_count INTEGER DEFAULT 0,
    mpin_change_time TEXT
)
""")

# 🔥 AUTO FIX (OLD DATABASE USERS KE LIYE)
try:
    cursor.execute("ALTER TABLE accounts ADD COLUMN lock_until TEXT")
except:
    pass


# 🔥 TRANSACTIONS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS transactions(
    txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT,
    txn_type TEXT,
    amount REAL,
    date TEXT,
    FOREIGN KEY(account_number) REFERENCES accounts(account_number)
)
""")


# 🔥 ADMINS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS admins(
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    admin_no TEXT,
    otp_secret TEXT
)
""")


# 🔥 LOANS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS loans(
    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT,
    loan_amount REAL,
    interest_rate REAL,
    loan_status TEXT DEFAULT 'Pending',
    loan_date TEXT,
    approved_date TEXT,
    FOREIGN KEY(account_number) REFERENCES accounts(account_number)
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS debit_cards(
    card_number TEXT PRIMARY KEY,
    account_number TEXT UNIQUE,
    network TEXT,
    variant TEXT,
    expiry_date TEXT,
    card_pin TEXT,
    issue_date TEXT,
    pos_limit REAL DEFAULT 0,
    card_status TEXT DEFAULT 'Active',
    pin_attempts INTEGER DEFAULT 0,
    pin_lock_until TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS card_requests(
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT,
    full_name TEXT,
    balance REAL,
    account_created TEXT,
    network TEXT,
    variant TEXT,
    amc REAL,
    withdraw_limit REAL,
    status TEXT DEFAULT 'Pending',
    rejection_count INTEGER DEFAULT 0,
    request_time TEXT,
    FOREIGN KEY(account_number) REFERENCES accounts(account_number)
)
""")
conn.commit()


    

# ==============================
# UTILITY FUNCTIONS
# ==============================
from flask import flash, get_flashed_messages

def hash_text(text):
    return hashlib.sha256(text.encode()).hexdigest()
def admin_exists():
    cursor.execute("SELECT 1 FROM admins LIMIT 1")
    return cursor.fetchone() is not None
@app.route("/")
def welcome():

    return render_template("welcome.html")
@app.route("/system_check")
def system_check():

    if not admin_exists():
        return redirect("/setup_admin")

    return redirect("/home")
@app.route("/help")
def help_page():
    return render_template("help.html")

@app.route("/about_bank")
def about_bank():
    return render_template("about_bank.html")

@app.route("/developers")
def developers():
    return render_template("developers.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/home")
def main_menu():

    if not admin_exists():
        return redirect("/setup_admin")

    return render_template("home.html")
@app.route("/security")
def security():
    return render_template("security.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from flask import session

def send_otp(receiver):

    # Generate OTP
    otp = f"{random.randint(0,999999):06}"

    # Save OTP in session
    session["otp"] = otp
    session["otp_expiry"] = (datetime.now() + timedelta(minutes=2)).isoformat()
    session["otp_attempts"] = 0

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    # ❌ Missing env check
    if not sender or not password:
        raise ValueError("Email credentials not set in .env")

    # 📧 HTML CONTENT
    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" style="background:white;border-radius:10px;margin-top:20px;">

                    <tr>
                        <td style="background:#2563eb;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>Secure OTP Verification</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">🔐 Your OTP Code</h3>

                            <p>Use the following OTP to complete your verification:</p>

                            <div style="background:#111;color:#fff;padding:15px;text-align:center;font-size:24px;border-radius:8px;letter-spacing:3px;">
                                {otp}
                            </div>

                            <p style="margin-top:15px;">
                                ⏳ This OTP is valid for <b>2 minutes</b>.
                            </p>

                            <h4 style="margin-top:20px;">⚠ Security Notice:</h4>
                            <ul>
                                <li>Do NOT share your OTP with anyone</li>
                                <li>Bharat Bank will NEVER ask for OTP</li>
                                <li>If you didn’t request this, ignore this email</li>
                            </ul>

                            <p style="margin-top:20px;">
                                Stay secure with <b>Bharat Bank</b> 🔒
                            </p>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                This is an automated message. Please do not reply.
                            </p>
                            <p style="font-size:12px;color:#777;">
                                © 2026 Bharat Bank | Secure Banking
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = "🔐 OTP Verification - Bharat Bank"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ OTP HTML Email Sent")

    except Exception as e:
        print("❌ Email error:", e)

    return otp
def send_mpin_change_alert(receiver):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        raise ValueError("Email credentials not set in .env")

    now = datetime.now().strftime("%d %b %Y %I:%M %p")

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" style="background:white;border-radius:10px;margin-top:20px;">

                    <tr>
                        <td style="background:#f59e0b;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>Security Alert</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">🔐 MPIN Changed Successfully</h3>

                            <p>Your MPIN has been successfully updated.</p>

                            <div style="background:#f1f1f1;padding:15px;border-radius:8px;">
                                <p><b>Status:</b> MPIN Changed ✅</p>
                                <p><b>Date & Time:</b> {now}</p>
                            </div>

                            <h4 style="margin-top:20px;">⚠ Important Security Notice:</h4>
                            <ul>
                                <li>If this was you → no action needed</li>
                                <li>If NOT → contact support immediately</li>
                                <li>Keep your MPIN confidential</li>
                            </ul>

                            <p style="margin-top:20px;">
                                Stay secure with <b>Bharat Bank</b> 🔒
                            </p>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                This is an automated message. Please do not reply.
                            </p>
                            <p style="font-size:12px;color:#777;">
                                © 2026 Bharat Bank | Secure Banking
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = "⚠ MPIN Changed - Security Alert"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ MPIN change HTML email sent")

    except Exception as e:
        print("❌ Email error:", e)

def send_loan_request_email(receiver, amount):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        raise ValueError("Email credentials not set in .env")

    now = datetime.now().strftime("%d %b %Y %I:%M %p")

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" style="background:white;border-radius:10px;margin-top:20px;">

                    <tr>
                        <td style="background:#3b82f6;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>Loan Request Received</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">📩 Loan Request Submitted</h3>

                            <p>We have successfully received your loan request.</p>

                            <div style="background:#f1f1f1;padding:15px;border-radius:8px;">
                                <p><b>Loan Amount:</b> ₹{amount}</p>
                                <p><b>Status:</b> Pending ⏳</p>
                                <p><b>Date & Time:</b> {now}</p>
                            </div>

                            <p style="margin-top:15px;">
                                Our team is reviewing your application. You will be notified once your loan is approved or rejected.
                            </p>

                            <h4 style="margin-top:20px;">🔐 Important Notice:</h4>
                            <ul>
                                <li>Never share OTP or account details</li>
                                <li>Bharat Bank never asks for MPIN/password</li>
                                <li>Beware of fraud calls</li>
                            </ul>

                            <p style="margin-top:20px;">
                                Thank you for choosing <b>Bharat Bank</b> ❤️
                            </p>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                © 2026 Bharat Bank | Secure Banking
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = "🏦 Loan Request Submitted - Bharat Bank"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ Loan request HTML email sent")

    except Exception as e:
        print("❌ Email error:", e)


def send_loan_status_email(receiver, amount, status):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        raise ValueError("Email credentials not set in .env")

    now = datetime.now().strftime("%d %b %Y %I:%M %p")

    # ================= APPROVED =================
    if status == "Approved":
        subject = "🏦 Loan Approved - Bharat Bank"

        html_content = f"""
        <html><body style="font-family:Arial;background:#f4f6f8;">
        <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px;">
            <h2 style="color:green;">🎉 Loan Approved</h2>

            <p>Your loan has been successfully approved.</p>

            <p><b>Amount:</b> ₹{amount}</p>
            <p><b>Status:</b> Approved ✅</p>
            <p><b>Date:</b> {now}</p>

            <h4>⚠ Important:</h4>
            <ul>
                <li>Pay EMI on time</li>
                <li>Late fees may apply</li>
                <li>Maintain good credit score</li>
            </ul>
        </div>
        </body></html>
        """

    # ================= REJECTED =================
    elif status == "Rejected":
        subject = "🏦 Loan Request Update - Bharat Bank"

        html_content = f"""
        <html><body style="font-family:Arial;background:#f4f6f8;">
        <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px;">
            <h2 style="color:red;">❌ Loan Rejected</h2>

            <p>Your loan request has been rejected.</p>

            <p><b>Amount:</b> ₹{amount}</p>
            <p><b>Status:</b> Rejected ❌</p>
            <p><b>Date:</b> {now}</p>

            <h4>Possible Reasons:</h4>
            <ul>
                <li>Eligibility not met</li>
                <li>Low balance history</li>
                <li>Existing loan active</li>
            </ul>
        </div>
        </body></html>
        """

    else:
        return

    # 📧 EMAIL SETUP
    msg = MIMEText(html_content, "html")
    msg["Subject"] = subject
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ Loan status email sent")

    except Exception as e:
        print("❌ Email error:", e)

def send_welcome_email(receiver, first_name, account_number):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        print("❌ Email credentials not set in .env")
        return

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f6f8;">
    
    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" style="background:#ffffff;border-radius:10px;margin-top:20px;">
                    
                    <tr>
                        <td style="background:#4a2c2a;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>Secure. Trusted. Digital.</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">Welcome, {first_name}! 🎉</h3>

                            <p>Your account has been successfully created.</p>

                            <div style="background:#f1f1f1;padding:15px;border-radius:8px;">
                                <p><b>Account Number:</b> {account_number}</p>
                                <p><b>Status:</b> Active ✅</p>
                            </div>

                            <h4 style="margin-top:20px;">What you can do:</h4>
                            <ul>
                                <li>💰 Deposit & Withdraw Money</li>
                                <li>💸 Transfer Funds</li>
                                <li>🏦 Apply for Loans</li>
                                <li>📊 Track Transactions</li>
                            </ul>

                            <h4>🔐 Security Tips:</h4>
                            <ul>
                                <li>Never share your OTP or MPIN</li>
                                <li>Bank never asks for confidential info</li>
                                <li>Always logout after use</li>
                            </ul>

                            <p style="margin-top:20px;">
                                Thank you for choosing <b>Bharat Bank</b> ❤️
                            </p>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                © 2026 Bharat Bank | All Rights Reserved
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = "🎉 Welcome to Bharat Bank"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ HTML Welcome Email Sent")

    except Exception as e:
        print("❌ Email error:", e)


def send_withdraw_email(receiver, amount, balance):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        print("❌ Email credentials not set in .env")
        return

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" style="background:#ffffff;border-radius:10px;margin-top:20px;">

                    <tr>
                        <td style="background:#dc2626;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>Withdrawal Alert</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">⚠ Transaction Alert</h3>

                            <p>A withdrawal has been made from your account.</p>

                            <div style="background:#f1f1f1;padding:15px;border-radius:8px;">
                                <p><b>Amount Withdrawn:</b> ₹{amount}</p>
                                <p><b>Remaining Balance:</b> ₹{balance}</p>
                                <p><b>Date & Time:</b> {datetime.now().strftime("%d %b %Y %I:%M %p")}</p>
                            </div>

                            <h4 style="margin-top:20px;">🔐 Security Notice:</h4>
                            <ul>
                                <li>If this was you → no action needed</li>
                                <li>If NOT → change MPIN immediately</li>
                                <li>Never share OTP or MPIN</li>
                            </ul>

                            <p style="margin-top:20px;">
                                Stay safe with <b>Bharat Bank</b> ❤️
                            </p>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                © 2026 Bharat Bank | Secure Banking System
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = "⚠ Withdrawal Alert - Bharat Bank"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ Withdrawal HTML Email Sent")

    except Exception as e:
        print("❌ Email error:", e)

def send_failed_login_email(receiver):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        print("❌ Email credentials not set in .env")
        return

    now = datetime.now().strftime("%d %b %Y %I:%M %p")

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" style="background:white;border-radius:10px;margin-top:20px;">

                    <tr>
                        <td style="background:#dc2626;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>Security Alert</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">⚠ Failed Login Attempt</h3>

                            <p>A wrong MPIN was entered for your account.</p>

                            <div style="background:#f1f1f1;padding:15px;border-radius:8px;">
                                <p><b>Status:</b> Failed Attempt ❌</p>
                                <p><b>Date & Time:</b> {now}</p>
                            </div>

                            <p style="margin-top:15px;">
                                ⚠ If you enter wrong MPIN <b>3 times</b>, your account will be temporarily locked for security.
                            </p>

                            <h4>🔐 Security Tips:</h4>
                            <ul>
                                <li>Do not share your MPIN</li>
                                <li>Change MPIN if suspicious activity</li>
                                <li>Contact support if this wasn’t you</li>
                            </ul>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                This is an automated message. Do not reply.
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = "⚠ Failed Login Attempt - Bharat Bank"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ Failed login email sent")

    except Exception as e:
        print("❌ Email error:", e)


def send_simple_email(receiver, message):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        print("❌ Email credentials not set in .env")
        return

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" 
                style="background:white;border-radius:10px;margin-top:20px;">

                    <tr>
                        <td style="background:#2563eb;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>Secure Banking Notification</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">📢 Important Update</h3>

                            <p style="font-size:15px;color:#444;">
                                {message}
                            </p>

                            <div style="background:#f1f1f1;padding:15px;border-radius:8px;margin-top:15px;">
                                <p><b>Status:</b> Processed ✅</p>
                                <p><b>Date & Time:</b> {datetime.now().strftime("%d %b %Y %I:%M %p")}</p>
                            </div>

                            <h4 style="margin-top:20px;">🔐 Security Reminder:</h4>
                            <ul>
                                <li>Never share your OTP or MPIN</li>
                                <li>Bharat Bank never asks for confidential details</li>
                                <li>Report suspicious activity immediately</li>
                            </ul>

                            <p style="margin-top:20px;">
                                Thank you for banking with <b>Bharat Bank</b> ❤️
                            </p>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                This is an automated message. Please do not reply.
                            </p>
                            <p style="font-size:12px;color:#777;">
                                © 2026 Bharat Bank | Secure Banking
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = "🏦 Bharat Bank Notification"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ HTML email sent")

    except Exception as e:
        print("❌ Email error:", e)

def send_cvv_otp_email(receiver, otp):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        print("❌ Email credentials not set in .env")
        return

    html = f"""
    <html>
    <body style="margin:0;font-family:Arial;background:#0f172a;color:white;">

    <div style="max-width:600px;margin:auto;padding:20px;">

        <div style="background:#dc2626;padding:20px;border-radius:10px;text-align:center;">
            <h2>🚨 Security Alert</h2>
            <p>CVV Access Request</p>
        </div>

        <div style="background:#111;padding:20px;margin-top:10px;border-radius:10px;">

            <h3>⚠ Sensitive Operation</h3>

            <p>You are trying to view your debit card CVV.</p>

            <div style="background:#000;padding:15px;text-align:center;
            font-size:26px;letter-spacing:5px;border-radius:8px;margin-top:10px;">
                {otp}
            </div>

            <p style="margin-top:15px;">
                ⏳ Valid for 2 minutes only
            </p>

            <ul>
                <li>Do NOT share this OTP</li>
                <li>Bank will NEVER ask for CVV</li>
                <li>If not you → ignore immediately</li>
            </ul>

        </div>

        <p style="text-align:center;margin-top:10px;font-size:12px;color:#aaa;">
            Bharat Bank Security System 🔒
        </p>

    </div>

    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = "🚨 CVV Access OTP - Bharat Bank"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ CVV OTP email sent")

    except Exception as e:
        print("❌ Email error:", e)


def send_card_view_otp_email(receiver, otp):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        print("❌ Email credentials not set in .env")
        return

    html = f"""
    <html>
    <body style="font-family:Arial;background:#f4f6f8;">

    <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px;">

        <h2 style="color:#2563eb;">🔐 Card Access Verification</h2>

        <p>You requested to view your debit card details.</p>

        <div style="background:#111;color:white;padding:15px;text-align:center;
        font-size:22px;border-radius:8px;">
            {otp}
        </div>

        <p style="margin-top:10px;">Valid for 2 minutes.</p>

        <p style="font-size:12px;color:#666;">
            Do not share this OTP with anyone.
        </p>

    </div>

    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = "🔐 Debit Card Access OTP"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ Card OTP email sent")

    except Exception as e:
        print("❌ Email error:", e)


def send_deactivation_otp_email(receiver, otp):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        print("❌ Email credentials not set in .env")
        return

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" 
                style="background:white;border-radius:10px;margin-top:20px;">

                    <tr>
                        <td style="background:#dc2626;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>Debit Card Deactivation Request</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">🔐 OTP Verification Required</h3>

                            <p>
                                You have requested to <b>Deactivate your Debit Card</b>.
                            </p>

                            <p>
                                Please use the OTP below to confirm this action:
                            </p>

                            <div style="background:#111;color:#fff;padding:15px;
                            text-align:center;font-size:24px;border-radius:8px;
                            letter-spacing:4px;">
                                {otp}
                            </div>

                            <p style="margin-top:15px;">
                                ⏳ This OTP is valid for <b>2 minutes</b>.
                            </p>

                            <h4 style="margin-top:20px;">⚠ Security Alert:</h4>
                            <ul>
                                <li>If this request was made by you → continue</li>
                                <li>If NOT → ignore immediately</li>
                                <li>Do NOT share this OTP with anyone</li>
                            </ul>

                            <p style="margin-top:20px;">
                                Your card will be permanently deactivated after verification.
                            </p>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                This is an automated message. Please do not reply.
                            </p>
                            <p style="font-size:12px;color:#777;">
                                © 2026 Bharat Bank | Secure Banking System
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = "⚠ Debit Card Deactivation OTP"
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ Deactivation OTP Email Sent")

    except Exception as e:
        print("❌ Email error:", e)

def send_pin_email(receiver, action):

    # 🔐 ENV VARIABLES
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        print("❌ Email credentials not set in .env")
        return

    now = datetime.now().strftime("%d %b %Y %I:%M %p")

    if action == "set":
        subject = "🔐 ATM PIN Set - Bharat Bank"
        message = "Your ATM PIN has been successfully set."
    else:
        subject = "🔐 ATM PIN Changed - Bharat Bank"
        message = "Your ATM PIN has been successfully changed."

    html_content = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center">

                <table width="600" cellpadding="20" cellspacing="0" style="background:white;border-radius:10px;margin-top:20px;">

                    <tr>
                        <td style="background:#2563eb;color:white;text-align:center;border-radius:10px 10px 0 0;">
                            <h2>🏦 Bharat Bank</h2>
                            <p>PIN Management</p>
                        </td>
                    </tr>

                    <tr>
                        <td>

                            <h3 style="color:#333;">🔐 ATM PIN Update</h3>

                            <p>{message}</p>

                            <div style="background:#f1f1f1;padding:15px;border-radius:8px;">
                                <p><b>Status:</b> PIN {'Set' if action == 'set' else 'Changed'} ✅</p>
                                <p><b>Date & Time:</b> {now}</p>
                            </div>

                            <h4 style="margin-top:20px;">🔐 Security Notice:</h4>
                            <ul>
                                <li>Keep your PIN confidential</li>
                                <li>Never share PIN with anyone</li>
                                <li>If this wasn't you, contact support immediately</li>
                            </ul>

                            <p style="margin-top:20px;">
                                Stay secure with <b>Bharat Bank</b> 🔒
                            </p>

                        </td>
                    </tr>

                    <tr>
                        <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                            <p style="font-size:12px;color:#555;">
                                This is an automated message. Please do not reply.
                            </p>
                            <p style="font-size:12px;color:#777;">
                                © 2026 Bharat Bank | Secure Banking
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html_content, "html")

    msg["Subject"] = subject
    msg["From"] = f"Bharat Bank <{sender}>"
    msg["To"] = receiver
    msg["Reply-To"] = sender

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        server.quit()

        print("✅ PIN Email Sent")

    except Exception as e:
        print("❌ Email error:", e)


def send_atm_pin_otp_email(receiver, otp):

    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    html = f"""
    <html>
    <body style="margin:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">

    <table width="600" style="background:white;border-radius:10px;margin-top:20px;" cellpadding="20">

        <tr>
            <td style="background:#2563eb;color:white;text-align:center;border-radius:10px 10px 0 0;">
                <h2>🏦 Bharat Bank</h2>
                <p>ATM PIN Security</p>
            </td>
        </tr>

        <tr>
            <td>

                <h3>🔐 ATM PIN Verification</h3>

                <p>You requested to <b>set/change your ATM PIN</b>.</p>

                <div style="background:#111;color:#fff;padding:15px;text-align:center;
                font-size:26px;border-radius:8px;letter-spacing:4px;">
                    {otp}
                </div>

                <p style="margin-top:15px;">
                    ⏳ This OTP is valid for <b>2 minutes</b>.
                </p>

                <h4>⚠ Security Warning:</h4>
                <ul>
                    <li>Do NOT share this OTP with anyone</li>
                    <li>If you didn’t request this → ignore immediately</li>
                    <li>Your account may be blocked for security</li>
                </ul>

                <p style="margin-top:20px;">
                    Stay secure with <b>Bharat Bank</b> 🔒
                </p>

            </td>
        </tr>

        <tr>
            <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                <p style="font-size:12px;">This is an automated message.</p>
            </td>
        </tr>

    </table>

    </td></tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = "🔐 ATM PIN OTP - Bharat Bank"
    msg["From"] = sender
    msg["To"] = receiver

    server = smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT")))
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receiver, msg.as_string())
    server.quit()


def send_pos_limit_otp_email(receiver, otp):

    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    html = f"""
    <html>
    <body style="margin:0;font-family:Arial;background:#f4f6f8;">

    <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">

    <table width="600" style="background:white;border-radius:10px;margin-top:20px;" cellpadding="20">

        <tr>
            <td style="background:#10b981;color:white;text-align:center;border-radius:10px 10px 0 0;">
                <h2>🏦 Bharat Bank</h2>
                <p>POS Limit Update</p>
            </td>
        </tr>

        <tr>
            <td>

                <h3>💳 POS Limit Verification</h3>

                <p>You are updating your <b>debit card spending limit</b>.</p>

                <div style="background:#111;color:#fff;padding:15px;text-align:center;
                font-size:26px;border-radius:8px;letter-spacing:4px;">
                    {otp}
                </div>

                <p style="margin-top:15px;">
                    ⏳ This OTP is valid for <b>2 minutes</b>.
                </p>

                <h4>⚠ Important Notice:</h4>
                <ul>
                    <li>Do NOT share this OTP</li>
                    <li>If you didn’t request this → ignore</li>
                    <li>Unauthorized changes may lock your card</li>
                </ul>

                <p style="margin-top:20px;">
                    Thank you for banking with <b>Bharat Bank</b> ❤️
                </p>

            </td>
        </tr>

        <tr>
            <td style="background:#eee;text-align:center;border-radius:0 0 10px 10px;">
                <p style="font-size:12px;">Secure Banking System © 2026</p>
            </td>
        </tr>

    </table>

    </td></tr>
    </table>

    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = "💳 POS Limit OTP - Bharat Bank"
    msg["From"] = sender
    msg["To"] = receiver

    server = smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT")))
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receiver, msg.as_string())
    server.quit()


# ================================================================
# UNIVERSAL ACTION OTP EMAIL
# (paste near your other send_* functions, e.g. after send_pos_limit_otp_email)
# ================================================================

def send_action_otp_email(receiver, otp, action_title, action_desc, accent_color="#2563eb", icon="🔐"):
    sender      = os.getenv("EMAIL_USER")
    password    = os.getenv("EMAIL_PASS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port   = int(os.getenv("SMTP_PORT"))

    if not sender or not password:
        raise ValueError("Email credentials not set in .env")

    now = datetime.now().strftime("%d %b %Y %I:%M %p")

    html = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f0f4f8;">
    <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:20px 0;">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:12px;overflow:hidden;
                      box-shadow:0 4px 20px rgba(0,0,0,0.08);">
            <tr>
                <td style="background:{accent_color};padding:24px 32px;text-align:center;">
                    <h1 style="margin:0;font-size:22px;color:white;">{icon} {action_title}</h1>
                    <p style="margin:6px 0 0;color:rgba(255,255,255,0.85);font-size:14px;">
                        Bharat Bank — Secure Verification
                    </p>
                </td>
            </tr>
            <tr>
                <td style="padding:32px;">
                    <div style="background:#f8fafc;border-left:4px solid {accent_color};
                                padding:14px 18px;border-radius:0 8px 8px 0;margin-bottom:24px;">
                        <p style="margin:0;font-size:14px;color:#334155;">
                            <strong>Why am I receiving this?</strong><br>{action_desc}
                        </p>
                    </div>
                    <p style="color:#475569;font-size:14px;margin-bottom:8px;">
                        Use the OTP below to complete this action:
                    </p>
                    <div style="background:#0f172a;border-radius:10px;padding:20px;
                                text-align:center;margin:16px 0;">
                        <span style="font-size:32px;font-weight:700;letter-spacing:8px;
                                     color:#ffffff;font-family:monospace;">{otp}</span>
                    </div>
                    <p style="color:#64748b;font-size:13px;margin-bottom:20px;">
                        ⏳ This OTP is valid for <strong>2 minutes</strong> from {now}.
                    </p>
                    <div style="background:#fff7ed;border:1px solid #fed7aa;
                                border-radius:8px;padding:16px;margin-top:20px;">
                        <p style="margin:0 0 8px;font-size:13px;font-weight:700;color:#9a3412;">
                            🔐 Security Reminders
                        </p>
                        <ul style="margin:0;padding-left:18px;font-size:13px;color:#78350f;line-height:1.8;">
                            <li>Do <strong>NOT</strong> share this OTP with anyone</li>
                            <li>Bharat Bank will <strong>NEVER</strong> call and ask for your OTP</li>
                            <li>If you did not request this, ignore this email and contact support</li>
                        </ul>
                    </div>
                </td>
            </tr>
            <tr>
                <td style="background:#f1f5f9;padding:16px 32px;text-align:center;
                           border-top:1px solid #e2e8f0;">
                    <p style="margin:0;font-size:12px;color:#94a3b8;">
                        This is an automated security email. Please do not reply.<br>
                        © 2026 Bharat Bank | Secure Banking System
                    </p>
                </td>
            </tr>
        </table>
    </td></tr>
    </table>
    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = f"{icon} {action_title} OTP — Bharat Bank"
    msg["From"]    = f"Bharat Bank <{sender}>"
    msg["To"]      = receiver
    msg["Reply-To"] = sender

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(sender, password)
    server.sendmail(sender, receiver, msg.as_string())
    server.quit()
    print(f"✅ Action OTP email sent: {action_title}")


# ================================================================
# OTP REQUEST ROUTES  (3 new ones — spending / replace / block)
# ================================================================

@app.route("/request_spending_otp", methods=["POST"])
def request_spending_otp():
    if "account" not in session:
        return "Unauthorized", 401
    acc_no = session["account"]
    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()
    if not data:
        return "Account not found", 404
    email = data[0]
    otp = str(random.randint(100000, 999999))
    session["spending_otp"]        = otp
    session["spending_otp_expiry"] = (datetime.now() + timedelta(minutes=2)).isoformat()
    try:
        send_action_otp_email(
            receiver=email, otp=otp,
            action_title="Spending Limits Update",
            action_desc="You requested to update your card's daily/monthly spending limits.",
            accent_color="#0ea5e9", icon="📊"
        )
    except Exception as e:
        print("❌ Spending OTP Email Error:", e)
        return "Failed to send OTP", 500
    return "OTP Sent", 200


@app.route("/request_replace_card_otp", methods=["POST"])
def request_replace_card_otp():
    if "account" not in session:
        return "Unauthorized", 401
    acc_no = session["account"]
    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()
    if not data:
        return "Account not found", 404
    email = data[0]
    otp = str(random.randint(100000, 999999))
    session["replace_card_otp"]        = otp
    session["replace_card_otp_expiry"] = (datetime.now() + timedelta(minutes=2)).isoformat()
    try:
        send_action_otp_email(
            receiver=email, otp=otp,
            action_title="Card Replacement / Re-issue",
            action_desc=(
                "You requested to replace or re-issue your debit card. "
                "Your current card will be deactivated once the new card is activated."
            ),
            accent_color="#a855f7", icon="💳"
        )
    except Exception as e:
        print("❌ Replace Card OTP Email Error:", e)
        return "Failed to send OTP", 500
    return "OTP Sent", 200


@app.route("/request_block_card_otp", methods=["POST"])
def request_block_card_otp():
    if "account" not in session:
        return "Unauthorized", 401
    acc_no = session["account"]
    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()
    if not data:
        return "Account not found", 404
    email = data[0]
    otp = str(random.randint(100000, 999999))
    session["block_card_otp"]        = otp
    session["block_card_otp_expiry"] = (datetime.now() + timedelta(minutes=2)).isoformat()
    try:
        send_action_otp_email(
            receiver=email, otp=otp,
            action_title="Card Block Request",
            action_desc=(
                "You requested to PERMANENTLY BLOCK your debit card. "
                "This action cannot be undone. "
                "If this was NOT you, please contact support immediately."
            ),
            accent_color="#dc2626", icon="🚨"
        )
    except Exception as e:
        print("❌ Block Card OTP Email Error:", e)
        return "Failed to send OTP", 500
    return "OTP Sent", 200


# ================================================================
# ACTION ROUTES
# ================================================================

@app.route("/view_card")
def view_card():
    if "account" not in session:
        return redirect("/user_login")
    acc_no = session["account"]
    cursor.execute("""
        SELECT d.card_number, d.expiry_date, d.variant,
               a.first_name, a.last_name
        FROM debit_cards d
        JOIN accounts a ON d.account_number = a.account_number
        WHERE d.account_number=? AND d.card_status='Active'
    """, (acc_no,))
    card = cursor.fetchone()
    if not card:
        flash("No active debit card found", "warning")
        return redirect("/dashboard")
    card_number, expiry_date, variant, first_name, last_name = card
    masked    = "XXXX XXXX XXXX " + card_number[-4:]
    full_name = f"{first_name} {last_name}".strip()
    return render_template(
        "view_card.html",
        card_number=masked,
        expiry=expiry_date,
        full_name=full_name,
        variant=variant
    )


@app.route("/spending_limits", methods=["POST"])
def spending_limits():
    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")
    acc_no = session["account"]

    mpin = request.form.get("mpin")
    otp  = request.form.get("otp")

    if not mpin or not otp:
        flash("All fields required", "danger")
        return redirect("/view_card")

    # OTP check
    expiry = session.get("spending_otp_expiry")
    if not expiry or datetime.now() > datetime.fromisoformat(expiry):
        flash("OTP expired. Please try again.", "danger")
        return redirect("/view_card")
    if otp != session.get("spending_otp"):
        flash("Invalid OTP", "danger")
        return redirect("/view_card")

    # MPIN check
    cursor.execute("SELECT mpin FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()
    if not data or hash_text(mpin) != data[0]:
        flash("Invalid MPIN", "danger")
        return redirect("/view_card")

    # Clean OTP
    session.pop("spending_otp", None)
    session.pop("spending_otp_expiry", None)

    # Fetch card limits
    cursor.execute("""
        SELECT pos_limit, variant FROM debit_cards WHERE account_number=?
    """, (acc_no,))
    card = cursor.fetchone()
    if not card:
        flash("No active card found", "warning")
        return redirect("/dashboard")

    pos_limit, variant = card
    max_limit = CARD_DETAILS.get(variant, {}).get("limit", 0) * 2

    return render_template(
        "spending_limits.html",
        pos_limit=pos_limit,
        variant=variant,
        max_limit=max_limit,
        verified=True
    )


@app.route("/replace_card", methods=["POST"])
def replace_card():
    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")
    acc_no = session["account"]

    mpin = request.form.get("mpin")
    otp  = request.form.get("otp")

    if not mpin or not otp:
        flash("All fields required", "danger")
        return redirect("/view_card")

    # OTP check
    expiry = session.get("replace_card_otp_expiry")
    if not expiry or datetime.now() > datetime.fromisoformat(expiry):
        flash("OTP expired. Please try again.", "danger")
        return redirect("/view_card")
    if otp != session.get("replace_card_otp"):
        flash("Invalid OTP", "danger")
        return redirect("/view_card")

    # MPIN check
    cursor.execute("SELECT mpin FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()
    if not data or hash_text(mpin) != data[0]:
        flash("Invalid MPIN", "danger")
        return redirect("/view_card")

    # Check active card
    cursor.execute("""
        SELECT card_number, variant FROM debit_cards
        WHERE account_number=? AND card_status='Active'
    """, (acc_no,))
    card = cursor.fetchone()
    if not card:
        flash("No active card found to replace", "warning")
        return redirect("/dashboard")

    old_card_number, variant = card

    try:
        network         = variant.split()[0]
        new_card_number = generate_card_number(network)
        new_expiry      = generate_expiry()

        cursor.execute("""
            UPDATE debit_cards SET card_status='Replaced'
            WHERE account_number=? AND card_number=?
        """, (acc_no, old_card_number))

        cursor.execute("""
            INSERT INTO debit_cards(
                card_number, account_number, network, variant,
                expiry_date, card_pin, issue_date
            ) VALUES(?,?,?,?,?,?,?)
        """, (new_card_number, acc_no, network, variant,
              new_expiry, "", datetime.now().isoformat()))

        conn.commit()

        session.pop("replace_card_otp", None)
        session.pop("replace_card_otp_expiry", None)

        cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
        email_data = cursor.fetchone()
        if email_data:
            try:
                send_simple_email(
                    email_data[0],
                    "✅ Your debit card has been replaced successfully. "
                    "Your old card is now deactivated and a new card has been issued."
                )
            except Exception as e:
                print("❌ Replace card email error:", e)

        flash("Card replaced successfully ✅. Your new card is now active.", "success")
        return redirect("/view_card")

    except Exception as e:
        conn.rollback()
        print("❌ Replace card error:", e)
        flash("Card replacement failed. Please try again.", "danger")
        return redirect("/dashboard")
    
@app.route("/update_pos_limit_direct", methods=["POST"])
def update_pos_limit_direct():
    if "account" not in session:
        return {"success": False, "error": "Not logged in"}, 401

    acc_no = session["account"]
    limit_str = request.form.get("limit")

    try:
        limit = float(limit_str)
    except (TypeError, ValueError):
        return {"success": False, "error": "Invalid limit amount"}

    if limit < 0:
        return {"success": False, "error": "Limit cannot be negative"}

    # Get card variant to check max allowed
    cursor.execute("SELECT variant FROM debit_cards WHERE account_number=?", (acc_no,))
    card = cursor.fetchone()
    if not card:
        return {"success": False, "error": "No card found"}

    variant   = card[0]
    max_limit = CARD_DETAILS.get(variant, {}).get("limit", 0) * 2

    if limit > max_limit:
        return {"success": False, "error": f"Limit cannot exceed ₹{int(max_limit)}"}

    try:
        cursor.execute("""
            UPDATE debit_cards SET pos_limit=? WHERE account_number=?
        """, (limit, acc_no))
        conn.commit()

        # Send confirmation email
        cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
        email_data = cursor.fetchone()
        if email_data:
            try:
                send_simple_email(
                    email_data[0],
                    f"✅ Your card's POS/daily spending limit has been updated to ₹{int(limit):,}."
                )
            except Exception as e:
                print("❌ Limit update email error:", e)

        return {"success": True}

    except Exception as e:
        conn.rollback()
        print("❌ Limit update error:", e)
        return {"success": False, "error": "Database error"}


@app.route("/block_card", methods=["POST"])
def block_card():
    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")
    acc_no = session["account"]

    mpin = request.form.get("mpin")
    otp  = request.form.get("otp")

    if not mpin or not otp:
        flash("All fields required", "danger")
        return redirect("/view_card")

    # OTP check
    expiry = session.get("block_card_otp_expiry")
    if not expiry or datetime.now() > datetime.fromisoformat(expiry):
        flash("OTP expired. Please try again.", "danger")
        return redirect("/view_card")
    if otp != session.get("block_card_otp"):
        flash("Invalid OTP", "danger")
        return redirect("/view_card")

    # MPIN check
    cursor.execute("SELECT mpin FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()
    if not data or hash_text(mpin) != data[0]:
        flash("Invalid MPIN", "danger")
        return redirect("/view_card")

    # Check card exists
    cursor.execute("""
        SELECT card_number FROM debit_cards
        WHERE account_number=? AND card_status='Active'
    """, (acc_no,))
    card = cursor.fetchone()
    if not card:
        flash("No active card found", "warning")
        return redirect("/dashboard")

    try:
        cursor.execute("""
            UPDATE debit_cards SET card_status='Blocked'
            WHERE account_number=?
        """, (acc_no,))
        conn.commit()

        session.pop("block_card_otp", None)
        session.pop("block_card_otp_expiry", None)

        cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
        email_data = cursor.fetchone()
        if email_data:
            try:
                send_action_otp_email(
                    receiver=email_data[0],
                    otp="------",
                    action_title="Card Blocked Successfully",
                    action_desc=(
                        "Your debit card has been permanently blocked as per your request. "
                        "If this was NOT you, contact Bharat Bank support immediately. "
                        "You will need to apply for a new card."
                    ),
                    accent_color="#dc2626",
                    icon="🚨"
                )
            except Exception as e:
                print("❌ Block card confirmation email error:", e)

        flash("Card permanently blocked ✅. Apply for a new card if needed.", "success")
        return redirect("/dashboard")

    except Exception as e:
        conn.rollback()
        print("❌ Block card error:", e)
        flash("Failed to block card. Please try again.", "danger")
        return redirect("/dashboard")

@app.route("/resend_deactivate_otp")
def resend_deactivate_otp():

    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")

    acc_no = session["account"]

    # 🔍 Get email
    cursor.execute("""
        SELECT email FROM accounts WHERE account_number=?
    """, (acc_no,))
    
    data = cursor.fetchone()

    if not data:
        flash("Account not found", "danger")
        return redirect("/dashboard")

    email = data[0]

    # 🔄 Generate OTP
    otp = str(random.randint(100000, 999999))

    session["deactivate_otp"] = otp
    session["deactivate_otp_expiry"] = (
        datetime.now() + timedelta(minutes=2)
    ).isoformat()

    # 📧 Send email
    try:
        send_deactivation_otp_email(email, otp)
        flash("New OTP sent successfully 📩", "success")

    except Exception as e:
        print("❌ OTP Email Error:", e)
        flash("Failed to send OTP. Try again later.", "danger")

    return redirect("/verify_deactivate_otp")

@app.route("/request_atm_pin_otp", methods=["POST"])
def request_atm_pin_otp():

    if "account" not in session:
        return "Unauthorized", 401

    acc_no = session["account"]

    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()

    if not data:
        return "Account not found", 404

    email = data[0]

    otp = str(random.randint(100000, 999999))

    session["atm_pin_otp"] = otp
    session["atm_pin_otp_expiry"] = (
        datetime.now() + timedelta(minutes=2)
    ).isoformat()

    # ✅ CORRECT FUNCTION
    send_atm_pin_otp_email(email, otp)

    return "OTP Sent"


@app.route("/request_pos_limit_otp", methods=["POST"])
def request_pos_limit_otp():

    if "account" not in session:
        return "Unauthorized", 401

    acc_no = session["account"]

    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()

    if not data:
        return "Account not found", 404

    email = data[0]

    otp = str(random.randint(100000, 999999))

    session["pos_limit_otp"] = otp
    session["pos_limit_otp_expiry"] = (
        datetime.now() + timedelta(minutes=2)
    ).isoformat()

    # ✅ CORRECT FUNCTION
    send_pos_limit_otp_email(email, otp)

    return "OTP Sent"



    
@app.route("/resend_otp")
def resend_otp():

    email = None

    # 🔐 Account creation flow check
    if "temp_account_data" in session:
        email = session["temp_account_data"].get("email")

    if not email:
        flash("Session expired. Please try again.", "danger")
        return redirect("/create_account")

    try:
        send_otp(email)
        flash("New OTP sent to your email 📩", "success")

    except Exception as e:
        print("❌ OTP Send Error:", e)
        flash("Failed to send OTP. Please try again.", "danger")

    return redirect("/verify_create_otp")

@app.route("/admin/change_admin", methods=["GET","POST"])
def change_admin():

    if request.method == "POST":

        old_username = request.form["old_username"]
        old_password = hash_text(request.form["old_password"])
        admin_no = request.form["admin_no"]

        new_username = request.form["new_username"]
        new_password = hash_text(request.form["new_password"])

        # Verify existing admin
        cursor.execute("""
        SELECT admin_id FROM admins
        WHERE username=? AND password=? AND admin_no=?
        """,(old_username, old_password, admin_no))

        admin = cursor.fetchone()

        if not admin:
            flash("Invalid admin credentials","danger")
            return redirect("/admin/change_admin")

        # Generate new admin number
        new_admin_no = generate_admin_no()

        cursor.execute("""
        UPDATE admins
        SET username=?, password=?, admin_no=?
        WHERE admin_id=?
        """,(new_username, new_password, new_admin_no, admin[0]))

        conn.commit()

        flash("Admin changed successfully","success")

        return render_template("admin_changed.html", admin_no=new_admin_no)

    return render_template("change_admin.html")

# ⬇️ CALL AFTER DEFINING


def validate_mobile(mobile):
    return mobile.isdigit() and len(mobile) == 10
import random

def generate_admin_no():
    return str(random.randint(100000,999999))

def validate_mpin(mpin):
    return mpin.isdigit() and len(mpin) == 6

def validate_age(dob):
    try:
        birth_date = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        print("❌ Invalid DOB format. Use YYYY-MM-DD.")
        return False

    today = datetime.today()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    return age >= 18

def generate_account_number(first_name):
    prefix = "1200"
    last_two = str(len(first_name) % 100).zfill(2)

    while True:
        random_part = str(random.randint(1000, 9999))
        acc_no = prefix + random_part + last_two
        cursor.execute("SELECT account_number FROM accounts WHERE account_number=?", (acc_no,))
        if not cursor.fetchone():
            return acc_no

def generate_cif_number():
    while True:
        cif = str(random.randint(10000000, 99999999))
        cursor.execute("SELECT cif_number FROM accounts WHERE cif_number=?", (cif,))
        if not cursor.fetchone():
            return cif  
        
def generate_card_number(network):
    prefix = "6082" if network == "RuPay" else "4123"

    while True:
        number = prefix + "".join([str(random.randint(0,9)) for _ in range(12)])
        cursor.execute("SELECT 1 FROM debit_cards WHERE card_number=?", (number,))
        if not cursor.fetchone():
            return number
        
@app.route("/verify_card_view", methods=["POST"])
def verify_card_view():

    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")

    acc_no = session["account"]

    mpin = request.form.get("mpin")
    
    otp = request.form.get("otp")

    # 🔐 MPIN CHECK
    cursor.execute("""
    SELECT mpin FROM accounts WHERE account_number=?
    """, (acc_no,))

    data = cursor.fetchone()

    if not data:
        flash("Account not found", "danger")
        return redirect("/dashboard")

    stored_mpin = data[0]

    if hash_text(mpin) != stored_mpin:
        flash("Invalid MPIN", "danger")
        return redirect("/verify_card")

    # 🔐 OTP CHECK
    if otp != session.get("card_otp"):
        flash("Invalid OTP", "danger")
        return redirect("/verify_card")
    expiry = session.get("card_otp_expiry")

    if not expiry or datetime.now() > datetime.fromisoformat(expiry):
        flash("OTP expired", "danger")
        return redirect("/verify_card")

    # 💳 FETCH CARD
    cursor.execute("""
    SELECT card_number, expiry_date FROM debit_cards
    WHERE account_number=?
    """, (acc_no,))

    card = cursor.fetchone()

    if not card:
        flash("No debit card found", "warning")
        return redirect("/dashboard")

    # 🔒 MASK CARD
    masked = "XXXX XXXX XXXX " + card[0][-4:]

    # ✅ SUCCESS
    return render_template(
        "view_card.html",
        card_number=masked,
        expiry=card[1]
    )



def generate_expiry():
    return (datetime.now() + timedelta(days=365*5)).strftime("%m/%y")
        
CARD_DETAILS = {
    "RuPay Classic": {"charge": 100, "limit": 20000},
    "RuPay Platinum": {"charge": 200, "limit": 40000},
    "RuPay Select": {"charge": 300, "limit": 60000},

    "Visa Classic": {"charge": 150, "limit": 25000},
    "Visa Gold": {"charge": 250, "limit": 50000},
    "Visa Platinum": {"charge": 350, "limit": 75000},
    "Visa Signature": {"charge": 500, "limit": 100000}
}
        
@app.route("/apply_debit_card", methods=["GET","POST"])
def apply_debit_card():

    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")
    
    acc_no = session["account"]

    # 🔥 Already has debit card
    cursor.execute("SELECT 1 FROM debit_cards WHERE account_number=?", (acc_no,))
    if cursor.fetchone():
        flash("You already have an active debit card.", "warning")
        return redirect("/dashboard")

    # 🔥 Check last request
    cursor.execute("""
        SELECT status, request_time 
        FROM card_requests 
        WHERE account_number=? 
        ORDER BY request_id DESC LIMIT 1
    """, (acc_no,))
    last_request = cursor.fetchone()

    if last_request:
        status, request_time = last_request

        if status in ['Pending', 'Approved']:
            flash("You have already applied for a debit card. Please wait for approval.", "warning")
            return redirect("/dashboard")
        
        if status == 'Rejected':
            if datetime.now() < datetime.fromisoformat(request_time) + timedelta(hours=24):
                flash("You can reapply after 24 hours from last rejection.", "warning")
                return redirect("/dashboard")

    # ==========================
    # POST REQUEST
    # ==========================
    if request.method == "POST":

        variant = request.form.get("variant")
        mpin = request.form.get("mpin")

        # 🔐 MPIN CHECK (NEW)
        cursor.execute("SELECT mpin FROM accounts WHERE account_number=?", (acc_no,))
        data = cursor.fetchone()

        if not data:
            flash("Account not found", "danger")
            return redirect("/dashboard")

        stored_mpin = data[0]

        if not mpin or hash_text(mpin) != stored_mpin:
            flash("Invalid MPIN", "danger")
            return redirect("/apply_debit_card")

        # 🔽 Variant validation
        if not variant or variant not in CARD_DETAILS:
            flash("Invalid card variant selected", "danger")
            return redirect("/apply_debit_card")

        details = CARD_DETAILS[variant]
        network = variant.split()[0]

        # 🔍 Fetch user
        cursor.execute("""
            SELECT first_name, last_name, balance, account_creation_date, email
            FROM accounts WHERE account_number=?
        """, (acc_no,))
        user = cursor.fetchone()

        if not user:
            flash("Account not found", "danger")
            return redirect("/dashboard")

        full_name = f"{user[0]} {user[1] or ''}".strip()

        try:
            # 💾 Insert request
            cursor.execute("""
                INSERT INTO card_requests(
                    account_number, full_name, balance, account_created,
                    network, variant, amc, withdraw_limit, request_time
                ) VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                acc_no, 
                full_name, 
                user[2], 
                user[3],
                network, 
                variant,
                details["charge"], 
                details["limit"],
                datetime.now().isoformat()
            ))
            
            conn.commit()

            # 📧 Email
            try:
                send_simple_email(
                    user[4],
                    "Your debit card application has been submitted successfully."
                )
            except:
                pass

            flash("Debit card application submitted successfully ✅", "success")
            return redirect("/dashboard")

        except Exception as e:
            conn.rollback()
            print("❌ ERROR:", e)

            flash("Something went wrong. Please try again.", "danger")
            return redirect("/apply_debit_card")

    # ==========================
    # GET REQUEST
    # ==========================
    return render_template("apply_card.html", CARD_DETAILS=CARD_DETAILS)

@app.route("/request_card_view_otp")
def request_card_view_otp():

    # 🔐 Session check
    if "account" not in session:
        return "Unauthorized", 401

    acc_no = session["account"]

    # 🔍 Get email
    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()

    if not data:
        return "Account not found", 404

    email = data[0]

    # 🔄 Generate OTP
    otp = str(random.randint(100000, 999999))

    session["card_otp"] = otp
    session["card_otp_expiry"] = (
        datetime.now() + timedelta(minutes=2)
    ).isoformat()

    # 📧 Send email
    try:
        send_card_view_otp_email(email, otp)
    except Exception as e:
        print("❌ Card OTP Error:", e)
        return "Failed to send OTP", 500

    return "OTP Sent"

@app.route("/request_cvv_otp", methods=["POST"])
def request_cvv_otp():

    # 🔐 Session check
    if "account" not in session:
        return "Unauthorized", 401

    acc_no = session["account"]

    # 🔍 Get email
    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()

    if not data:
        return "Account not found", 404

    email = data[0]

    # 🔄 Generate OTP
    otp = str(random.randint(100000, 999999))

    session["cvv_otp"] = otp
    session["cvv_otp_expiry"] = (
        datetime.now() + timedelta(minutes=2)
    ).isoformat()

    # 📧 Send email
    try:
        send_cvv_otp_email(email, otp)
    except Exception as e:
        print("❌ CVV OTP Error:", e)
        return "Failed to send OTP", 500

    return "OTP Sent"
        
@app.route("/deposit", methods=["GET","POST"])
def deposit_money():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    if request.method == "POST":

        try:
            amount = float(request.form["amount"])
        except ValueError:
            flash("Invalid amount","danger")
            return redirect("/deposit")

        # Amount validation
        if amount <= 0:
            flash("Amount must be greater than 0","danger")
            return redirect("/deposit")

        # Deposit limit
        if amount > 100000:
            flash("Maximum deposit limit is ₹100000","danger")
            return redirect("/deposit")

        cursor.execute(
        "SELECT account_status FROM accounts WHERE account_number=?",
        (acc_no,)
        )

        status = cursor.fetchone()

        if status[0] != "Active":
            flash("Account is not active","danger")
            return redirect("/deposit")

        try:

            cursor.execute(
            "UPDATE accounts SET balance = balance + ? WHERE account_number=?",
            (amount, acc_no)
            )

            cursor.execute("""
            INSERT INTO transactions(account_number,txn_type,amount,date)
            VALUES(?,?,?,?)
            """,(acc_no,"Deposit",amount,datetime.now()))

            conn.commit()

            flash(f"₹{amount} deposited successfully","success")
            return redirect("/dashboard")

        except:

            conn.rollback()
            flash("Deposit failed","danger")
            return redirect("/deposit")

    return render_template("deposit.html")
@app.route("/verify_deactivate_otp", methods=["GET","POST"])
def verify_deactivate_otp():

    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")

    acc_no = session["account"]

    if request.method == "POST":

        entered_otp = request.form.get("otp")

        # ❌ OTP missing
        if not entered_otp:
            flash("Please enter OTP", "danger")
            return redirect("/verify_deactivate_otp")

        # ⏳ EXPIRY CHECK
        expiry = session.get("deactivate_otp_expiry")

        if not expiry:
            flash("Session expired. Please try again.", "danger")
            return redirect("/dashboard")

        if datetime.now() > datetime.fromisoformat(expiry):
            flash("OTP expired", "danger")
            return redirect("/dashboard")

        # ❌ WRONG OTP
        if entered_otp != session.get("deactivate_otp"):
            flash("Invalid OTP", "danger")
            return redirect("/verify_deactivate_otp")

        # 💳 CHECK CARD EXISTS
        cursor.execute("SELECT 1 FROM debit_cards WHERE account_number=?", (acc_no,))
        if not cursor.fetchone():
            flash("No active debit card found", "warning")
            return redirect("/dashboard")

        try:
            # 🔥 BETTER: deactivate instead of delete
            cursor.execute("""
            UPDATE debit_cards
            SET card_status='Deactivated'
            WHERE account_number=?
            """, (acc_no,))

            conn.commit()

            # 🧹 CLEAN SESSION
            session.pop("deactivate_otp", None)
            session.pop("deactivate_otp_expiry", None)

            flash("Debit card deactivated successfully ✅", "success")
            return redirect("/dashboard")

        except Exception as e:
            conn.rollback()
            print("❌ ERROR:", e)

            flash("Something went wrong", "danger")
            return redirect("/dashboard")

    # GET request → show page
    return render_template("verify_deactivate_otp.html")

@app.route("/withdraw", methods=["GET","POST"])
def withdraw_money():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    # 🔐 ENV CONFIG
    MAX_LIMIT = float(os.getenv("MAX_WITHDRAW_LIMIT", 50000))
    MAX_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 3))
    LOCK_HOURS = int(os.getenv("ACCOUNT_LOCK_HOURS", 12))

    if request.method == "POST":

        mpin = request.form["mpin"]

        try:
            amount = float(request.form["amount"])
        except:
            flash("Invalid amount", "danger")
            return redirect("/withdraw")

        if amount <= 0:
            flash("Amount must be greater than 0", "danger")
            return redirect("/withdraw")

        if amount > MAX_LIMIT:
            flash(f"Maximum withdrawal limit is ₹{int(MAX_LIMIT)}", "danger")
            return redirect("/withdraw")

        # 🔍 FETCH DATA
        cursor.execute("""
        SELECT mpin, balance, account_status, login_attempts, lock_until
        FROM accounts WHERE account_number=?
        """, (acc_no,))

        result = cursor.fetchone()

        if not result:
            flash("Account not found", "danger")
            return redirect("/withdraw")

        stored_mpin, balance, status, attempts, lock_until = result

        # 🔒 LOCK CHECK
        if lock_until:
            unlock_time = datetime.fromisoformat(lock_until)

            if datetime.now() < unlock_time:
                flash(f"Account locked till {unlock_time.strftime('%I:%M %p')}", "danger")
                return redirect("/withdraw")
            else:
                cursor.execute("""
                UPDATE accounts 
                SET login_attempts=0, lock_until=NULL, account_status='Active'
                WHERE account_number=?
                """, (acc_no,))
                conn.commit()
                attempts = 0

        # 🔒 STATUS CHECK
        if status == "Locked":
            flash("Account is locked. Try later or contact admin.", "danger")
            return redirect("/withdraw")

        if status != "Active":
            flash("Account is not active", "danger")
            return redirect("/withdraw")

        # ❌ WRONG MPIN
        if hash_text(mpin) != stored_mpin:

            attempts += 1

            if attempts >= MAX_ATTEMPTS:
                lock_time = datetime.now() + timedelta(hours=LOCK_HOURS)

                cursor.execute("""
                UPDATE accounts 
                SET login_attempts=?, account_status='Locked', lock_until=?
                WHERE account_number=?
                """, (attempts, lock_time.isoformat(), acc_no))

                conn.commit()

                flash(f"Account locked for {LOCK_HOURS} hours due to wrong MPIN attempts", "danger")

            else:
                cursor.execute("""
                UPDATE accounts SET login_attempts=?
                WHERE account_number=?
                """, (attempts, acc_no))

                conn.commit()

                flash(f"Wrong MPIN! Attempts left: {MAX_ATTEMPTS - attempts}", "danger")

            return redirect("/withdraw")

        # ✅ RESET ATTEMPTS
        cursor.execute("""
        UPDATE accounts 
        SET login_attempts=0, lock_until=NULL, account_status='Active'
        WHERE account_number=?
        """, (acc_no,))
        conn.commit()

        # 💰 BALANCE CHECK
        if amount > balance:
            flash("Insufficient balance", "danger")
            return redirect("/withdraw")

        try:

            # 💰 DEDUCT
            cursor.execute("""
            UPDATE accounts SET balance = balance - ?
            WHERE account_number=?
            """, (amount, acc_no))

            # 📊 TRANSACTION
            cursor.execute("""
            INSERT INTO transactions(account_number,txn_type,amount,date)
            VALUES(?,?,?,?)
            """, (acc_no, "Withdraw", amount, datetime.now()))

            conn.commit()

            # 📧 EMAIL
            cursor.execute("SELECT email, balance FROM accounts WHERE account_number=?", (acc_no,))
            data = cursor.fetchone()

            if data:
                email, updated_balance = data

                try:
                    send_withdraw_email(email, amount, updated_balance)
                except Exception as e:
                    print("❌ Email Error:", e)

            flash(f"₹{amount} withdrawn successfully", "success")
            return redirect("/dashboard")

        except Exception as e:
            conn.rollback()
            print("❌ ERROR:", e)
            flash("Withdrawal failed. Please try again.", "danger")
            return redirect("/withdraw")

    return render_template("withdraw.html")
@app.route("/view_card_secure", methods=["GET","POST"])
def view_card_secure():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    # ================= POST =================
    if request.method == "POST":

        mpin = request.form.get("mpin")
        otp = request.form.get("otp")

        # Basic validation
        if not mpin or not otp:
            flash("All fields required", "danger")
            return redirect("/view_card_secure")

        # OTP expiry check
        expiry = session.get("card_otp_expiry")
        if not expiry or datetime.now() > datetime.fromisoformat(expiry):
            flash("OTP expired", "danger")
            return redirect("/view_card_secure")

        # OTP verify
        if otp != session.get("card_otp"):
            flash("Invalid OTP", "danger")
            return redirect("/view_card_secure")

        # Fetch user + MPIN
        cursor.execute("""
        SELECT mpin, first_name, last_name 
        FROM accounts WHERE account_number=?
        """, (acc_no,))
        user = cursor.fetchone()

        if not user:
            flash("Account not found", "danger")
            return redirect("/dashboard")

        stored_mpin, first_name, last_name = user

        if hash_text(mpin) != stored_mpin:
            flash("Invalid MPIN", "danger")
            return redirect("/view_card_secure")

        # Fetch card (NO card_status condition for now)
        cursor.execute("""
        SELECT card_number, expiry_date, variant 
        FROM debit_cards
        WHERE account_number=?
        """,(acc_no,))
        
        card = cursor.fetchone()

        if not card:
            flash("No debit card found", "warning")
            return redirect("/dashboard")

        card_number, expiry_date, variant = card

        # Full name
        full_name = f"{first_name} {last_name}".strip()

        # Clear OTP
        session.pop("card_otp", None)
        session.pop("card_otp_expiry", None)

        # ✅ FINAL RENDER
        return render_template(
            "view_card.html",
            card_number=card_number,
            expiry=expiry_date,
            full_name=full_name,
            variant=variant
        )

    # ================= GET =================
    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    email = cursor.fetchone()[0]

    otp = str(random.randint(100000,999999))

    session["card_otp"] = otp
    session["card_otp_expiry"] = (datetime.now() + timedelta(minutes=2)).isoformat()

    send_card_view_otp_email(email, otp)

    flash("OTP sent to your email", "info")

    return render_template("verify_card.html")
from datetime import datetime

@app.route("/view_cvv", methods=["POST"])
def view_cvv():

    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")

    acc_no = session["account"]

    entered_otp = request.form.get("otp")
    mpin = request.form.get("mpin")

    if not entered_otp or not mpin:
        flash("All fields required", "danger")
        return redirect("/dashboard")

    # OTP expiry
    expiry = session.get("cvv_otp_expiry")

    if not expiry:
        flash("OTP expired", "danger")
        return redirect("/dashboard")

    try:
        expiry_time = datetime.fromisoformat(expiry)
    except:
        flash("OTP expired", "danger")
        return redirect("/dashboard")

    if datetime.now() > expiry_time:
        flash("OTP expired", "danger")
        return redirect("/dashboard")

    # OTP check
    if entered_otp != session.get("cvv_otp"):
        flash("Invalid OTP", "danger")
        return redirect("/dashboard")

    # MPIN verify
    cursor.execute("SELECT mpin FROM accounts WHERE account_number=?", (acc_no,))
    data = cursor.fetchone()

    if not data or hash_text(mpin) != data[0]:
        flash("Invalid MPIN", "danger")
        return redirect("/dashboard")

    # 💳 CHECK CARD
    cursor.execute("""
    SELECT 1 FROM debit_cards 
    WHERE account_number=? AND card_status='Active'
    """, (acc_no,))
    
    if not cursor.fetchone():
        flash("No active card found", "warning")
        return redirect("/dashboard")

    # 🔥 TEMP CVV (SECURE)
    import random
    from datetime import timedelta

    temp_cvv = str(random.randint(100, 999))

    session["temp_cvv"] = temp_cvv
    session["temp_cvv_expiry"] = (datetime.now() + timedelta(seconds=30)).isoformat()

    # cleanup otp
    session.pop("cvv_otp", None)
    session.pop("cvv_otp_expiry", None)

    return render_template("show_cvv.html", cvv=temp_cvv)

@app.route("/set_pos_limit", methods=["POST"])
def set_pos_limit():

    # 🔒 Session check
    if "account" not in session:
        flash("Please login first", "danger")
        return redirect("/user_login")

    acc_no = session["account"]

    mpin = request.form.get("mpin")
    otp = request.form.get("otp")
    limit_str = request.form.get("limit")

    # ❌ Missing input
    if not mpin or not otp or not limit_str:
        flash("All fields required", "danger")
        return redirect("/dashboard")

    # 🔐 OTP EXPIRY CHECK
    expiry = session.get("pos_limit_otp_expiry")

    if not expiry:
        flash("OTP expired", "danger")
        return redirect("/dashboard")

    try:
        expiry_time = datetime.fromisoformat(expiry)
    except:
        flash("OTP expired", "danger")
        return redirect("/dashboard")

    if datetime.now() > expiry_time:
        flash("OTP expired", "danger")
        return redirect("/dashboard")

    # 🔐 OTP MATCH
    if otp != session.get("pos_limit_otp"):
        flash("Invalid OTP", "danger")
        return redirect("/dashboard")

    # 🔐 MPIN CHECK
    cursor.execute("""
    SELECT mpin FROM accounts WHERE account_number=?
    """, (acc_no,))
    
    data = cursor.fetchone()

    if not data:
        flash("Account not found", "danger")
        return redirect("/dashboard")

    stored_mpin = data[0]

    if hash_text(mpin) != stored_mpin:
        flash("Invalid MPIN", "danger")
        return redirect("/dashboard")

    # 💰 LIMIT VALIDATION
    try:
        limit = float(limit_str)
    except ValueError:
        flash("Invalid limit amount", "danger")
        return redirect("/dashboard")

    if limit < 0:
        flash("Limit cannot be negative", "danger")
        return redirect("/dashboard")

    # 💳 GET CARD
    cursor.execute("""
    SELECT variant FROM debit_cards WHERE account_number=?
    """, (acc_no,))
    
    card = cursor.fetchone()

    if not card:
        flash("No debit card found", "warning")
        return redirect("/dashboard")

    variant = card[0]

    if variant not in CARD_DETAILS:
        flash("Invalid card type", "danger")
        return redirect("/dashboard")

    max_limit = CARD_DETAILS[variant]["limit"] * 2

    if limit > max_limit:
        flash(f"Limit must be between 0 and ₹{max_limit}", "danger")
        return redirect("/dashboard")

    # ✅ UPDATE
    try:
        cursor.execute("""
        UPDATE debit_cards SET pos_limit=? WHERE account_number=?
        """, (limit, acc_no))

        conn.commit()

        # 🔥 CLEAN OTP
        session.pop("pos_limit_otp", None)
        session.pop("pos_limit_otp_expiry", None)

        flash("POS limit updated successfully ✅", "success")
        return redirect("/dashboard")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR:", e)

        flash("Failed to update POS limit", "danger")
        return redirect("/dashboard")
    
@app.route("/set_atm_pin", methods=["POST"])
def set_atm_pin():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    mpin = request.form.get("mpin")
    otp = request.form.get("otp")
    new_pin = request.form.get("new_pin")
    old_pin = request.form.get("old_pin")

    # ❌ Missing input
    if not mpin or not otp or not new_pin:
        flash("All fields required", "danger")
        return redirect("/security")

    # 🔐 OTP EXPIRY CHECK
    expiry = session.get("atm_pin_otp_expiry")

    if not expiry or datetime.now() > datetime.fromisoformat(expiry):
        flash("OTP expired", "danger")
        return redirect("/security")

    # 🔐 OTP MATCH (FIXED)
    if otp != session.get("atm_pin_otp"):
        flash("Invalid OTP", "danger")
        return redirect("/security")

    # 🔐 MPIN CHECK
    cursor.execute("SELECT mpin FROM accounts WHERE account_number=?", (acc_no,))
    stored_mpin = cursor.fetchone()[0]

    if hash_text(mpin) != stored_mpin:
        flash("Wrong MPIN", "danger")
        return redirect("/security")

    # 💳 FETCH CARD DATA (FIXED)
    cursor.execute("""
    SELECT card_pin, pin_attempts, pin_lock_until
    FROM debit_cards WHERE account_number=?
    """, (acc_no,))
    
    result = cursor.fetchone()

    if not result:
        flash("Card not found", "danger")
        return redirect("/security")

    stored_pin, attempts, lock_until = result

    # 🔒 CHECK LOCK
    if lock_until:
        unlock_time = datetime.fromisoformat(lock_until)

        if datetime.now() < unlock_time:
            flash(f"PIN change locked till {unlock_time.strftime('%I:%M %p')}", "danger")
            return redirect("/security")
        else:
            cursor.execute("""
            UPDATE debit_cards SET pin_attempts=0, pin_lock_until=NULL
            WHERE account_number=?
            """, (acc_no,))
            conn.commit()
            attempts = 0

    # 🔢 PIN VALIDATION
    if len(new_pin) != 4 or not new_pin.isdigit():
        flash("PIN must be 4 digits", "danger")
        return redirect("/security")

    # ==============================
    # 🔥 FIRST TIME SET PIN
    # ==============================
    if not stored_pin:

        cursor.execute("""
        UPDATE debit_cards SET card_pin=?, pin_attempts=0
        WHERE account_number=?
        """, (hash_text(new_pin), acc_no))
        conn.commit()

        action = "set"

    # ==============================
    # 🔥 CHANGE PIN
    # ==============================
    else:

        if not old_pin:
            flash("Old PIN required", "danger")
            return redirect("/security")

        # ❌ WRONG OLD PIN
        if hash_text(old_pin) != stored_pin:

            attempts += 1

            if attempts >= 3:
                lock_time = datetime.now() + timedelta(hours=24)

                cursor.execute("""
                UPDATE debit_cards 
                SET pin_attempts=?, pin_lock_until=?
                WHERE account_number=?
                """, (attempts, lock_time.isoformat(), acc_no))
                conn.commit()

                flash("Too many wrong attempts. Locked for 24 hours", "danger")

            else:
                cursor.execute("""
                UPDATE debit_cards SET pin_attempts=?
                WHERE account_number=?
                """, (attempts, acc_no))
                conn.commit()

                flash(f"Wrong Old PIN! Attempts left: {3 - attempts}", "danger")

            return redirect("/security")

        # ✅ RESET ATTEMPTS
        cursor.execute("""
        UPDATE debit_cards SET pin_attempts=0, pin_lock_until=NULL
        WHERE account_number=?
        """, (acc_no,))
        conn.commit()

        # 🔄 UPDATE PIN
        cursor.execute("""
        UPDATE debit_cards SET card_pin=?
        WHERE account_number=?
        """, (hash_text(new_pin), acc_no))
        conn.commit()

        action = "changed"

    # 🔥 CLEAN OTP (VERY IMPORTANT)
    session.pop("atm_pin_otp", None)
    session.pop("atm_pin_otp_expiry", None)

    # 📧 EMAIL
    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    email = cursor.fetchone()[0]

    send_pin_email(email, action)

    flash(f"ATM PIN {action} successfully", "success")
    return redirect("/dashboard")

@app.route("/transactions")
def view_transactions():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    # Check account status
    cursor.execute(
    "SELECT account_status FROM accounts WHERE account_number=?",
    (acc_no,)
    )

    status = cursor.fetchone()

    if not status:
        flash("Account not found","danger")
        return redirect("/dashboard")

    if status[0] != "Active":
        flash("Account is not active", "danger")
        return redirect("/dashboard")

    # Fetch transactions
    cursor.execute("""
    SELECT txn_type, amount, date
    FROM transactions
    WHERE account_number=?
    ORDER BY txn_id DESC
    LIMIT 50
    """,(acc_no,))

    records = cursor.fetchall()

    html = """
    <h2>Transaction History</h2>

    <table border="1" cellpadding="8">
    <tr>
        <th>Date & Time</th>
        <th>Transaction Type</th>
        <th>Amount</th>
    </tr>
    """

    if not records:
        html += "<tr><td colspan='3'>No transactions found</td></tr>"

    for r in records:
        html += f"""
        <tr>
            <td>{r[2]}</td>
            <td>{r[0]}</td>
            <td>₹{r[1]}</td>
        </tr>
        """

    html += """
    </table>
    <br>
    <a href="/dashboard">⬅ Back to Dashboard</a>
    """

    return html

# ==============================
# ACCOUNT CREATION
# ==============================
@app.route("/create_account", methods=["GET","POST"])
def create_account():

    if request.method == "POST":

        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        father_name = request.form["father_name"].strip()
        dob = request.form["dob"].strip()
        address = request.form["address"].strip()
        email = request.form["email"].strip()
        mobile = request.form["mobile"].strip()
        nominee_name = request.form["nominee_name"].strip()
        nominee_relation = request.form["nominee_relation"].strip()
        nominee_mobile = request.form["nominee_mobile"].strip()
        type_choice = request.form["account_type"]
        mpin = request.form["mpin"].strip()

        # VALIDATION
        if not validate_mobile(mobile):
            flash("Invalid mobile number","danger")
            return redirect("/create_account")

        if not validate_mobile(nominee_mobile):
            flash("Invalid nominee mobile number","danger")
            return redirect("/create_account")

        if not validate_age(dob):
            flash("Age must be 18 or above","danger")
            return redirect("/create_account")

        if not validate_mpin(mpin):
            flash("MPIN must be exactly 6 digits","danger")
            return redirect("/create_account")

        # SEND OTP
        otp = send_otp(email)

        # store otp + form data in session
        
        session["temp_account_data"] = request.form

        flash("OTP sent to your email","info")

        return redirect("/verify_create_otp")

    return render_template("create_account.html", success=False)

@app.route("/verify_create_otp", methods=["GET","POST"])
def verify_create_otp():

    if request.method == "POST":

        entered_otp = request.form["otp"].strip()

        # Check OTP expiry
        expiry_time = datetime.fromisoformat(session.get("otp_expiry"))

        if datetime.now() > expiry_time:
            flash("OTP expired. Please create account again.","danger")
            return redirect("/create_account")

        # Track attempts
        session["otp_attempts"] += 1

        if session["otp_attempts"] > 3:
            flash("Too many wrong OTP attempts. Please try again.","danger")
            return redirect("/create_account")

        # Verify OTP
        if entered_otp != session.get("otp"):
            flash("Invalid OTP","danger")
            return redirect("/verify_create_otp")

        # OTP correct → continue account creation
        data = session.get("temp_account_data")

        first_name = data["first_name"].strip()
        last_name = data["last_name"].strip()
        father_name = data["father_name"].strip()
        dob = data["dob"].strip()
        address = data["address"].strip()
        email = data["email"].strip()
        mobile = data["mobile"].strip()
        nominee_name = data["nominee_name"].strip()
        nominee_relation = data["nominee_relation"].strip()
        nominee_mobile = data["nominee_mobile"].strip()
        mpin = hash_text(data["mpin"].strip())

        account_type = "Savings" if data["account_type"] == "1" else "Current"

        account_number = generate_account_number(first_name)
        cif_number = generate_cif_number()

        try:
            cursor.execute("""
            INSERT INTO accounts(
            account_number, cif_number, first_name, last_name, father_name,
            dob, address, email, mobile,
            nominee_name, nominee_relation, nominee_mobile,
            account_type, mpin, account_creation_date
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,(
                account_number,
                cif_number,
                first_name,
                last_name,
                father_name,
                dob,
                address,
                email,
                mobile,
                nominee_name,
                nominee_relation,
                nominee_mobile,
                account_type,
                mpin,
                datetime.today().strftime("%Y-%m-%d")
            ))

            conn.commit()   # ✅ FIRST SAVE DATA

            # 🔥 THEN SEND EMAIL (IMPORTANT)
            send_welcome_email(email, first_name, account_number)

        except sqlite3.IntegrityError:
            conn.rollback()
            flash("Email or Mobile already registered!", "danger")
            return redirect("/create_account")

        except Exception as e:
            conn.rollback()
            print("❌ ERROR:", e)
            flash("Something went wrong","danger")
            return redirect("/create_account")

        # Clear session
        session.pop("otp", None)
        session.pop("otp_expiry", None)
        session.pop("otp_attempts", None)
        session.pop("temp_account_data", None)

        return render_template(
            "create_account.html",
            success=True,
            account_number=account_number,
            cif_number=cif_number
        )

    return render_template("verify_otp.html")
# ==============================
# USER LOGIN
# ==============================

@app.route("/user_login", methods=["GET","POST"])
def user_login():

    if request.method == "POST":

        acc_no = request.form.get("account", "").strip()
        mpin = request.form.get("mpin", "").strip()

        if not acc_no or not mpin:
            flash("Please fill all fields", "danger")
            return redirect("/user_login")

        cursor.execute("""
        SELECT mpin, login_attempts, account_status, lock_until, email
        FROM accounts WHERE account_number=?
        """, (acc_no,))

        result = cursor.fetchone()

        if not result:
            flash("Account not found", "danger")
            return redirect("/user_login")

        stored_mpin, attempts, status, lock_until, email = result

        # 🔒 CHECK TIME LOCK
        if lock_until:
            unlock_time = datetime.fromisoformat(lock_until)

            if datetime.now() < unlock_time:
                flash(f"Account locked till {unlock_time.strftime('%I:%M %p')}", "danger")
                return redirect("/user_login")
            else:
                # ✅ AUTO UNLOCK
                cursor.execute("""
                UPDATE accounts 
                SET login_attempts=0, lock_until=NULL, account_status='Active'
                WHERE account_number=?
                """, (acc_no,))
                conn.commit()
                attempts = 0
                status = "Active"

        # 🔒 STATUS CHECK
        if status == "Locked":
            flash("Account is locked. Try later or contact admin.", "danger")
            return redirect("/user_login")

        # ✅ CORRECT MPIN
        if hash_text(mpin) == stored_mpin:

            cursor.execute("""
            UPDATE accounts SET login_attempts=0, lock_until=NULL
            WHERE account_number=?
            """, (acc_no,))

            conn.commit()

            session["account"] = acc_no
            return redirect("/dashboard")

        # ❌ WRONG MPIN
        attempts += 1

        # 📧 SEND EMAIL ALERT
        if email:
            try:
                send_failed_login_email(email)
            except:
                pass

        if attempts >= 3:

            lock_time = datetime.now() + timedelta(hours=12)

            cursor.execute("""
            UPDATE accounts 
            SET login_attempts=?, account_status='Locked', lock_until=?
            WHERE account_number=?
            """, (attempts, lock_time.isoformat(), acc_no))

            conn.commit()

            flash("Account locked for 12 hours due to multiple wrong attempts", "danger")

        else:
            cursor.execute("""
            UPDATE accounts SET login_attempts=?
            WHERE account_number=?
            """, (attempts, acc_no))

            conn.commit()

            flash(f"Wrong MPIN. Attempts left: {3 - attempts}", "danger")

        return redirect("/user_login")

    return render_template("user_login.html")

# ==============================
# ADMIN LOGIN
# ==============================
@app.route("/setup_admin", methods=["GET","POST"])
def setup_admin():

    if admin_exists():
        return redirect("/home")

    if request.method == "POST":

        username = request.form["username"]
        password = hash_text(request.form["password"])

        admin_no = generate_admin_no()

        cursor.execute("""
        INSERT INTO admins(username,password,admin_no)
        VALUES(?,?,?)
        """,(username,password,admin_no))

        conn.commit()

        return render_template(
            "admin_created.html",
            admin_no=admin_no
        )

    return render_template("setup_admin.html")
@app.route("/admin_login", methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        session.clear()   # ✅ IMPORTANT

        username = request.form["username"]
        password = hash_text(request.form["password"])

        cursor.execute("""
        SELECT * FROM admins
        WHERE username=? AND password=?
        """,(username,password))

        admin = cursor.fetchone()

        if not admin:
            flash("Invalid admin credentials","danger")
            return redirect("/admin_login")

        session["admin"] = admin[0]

        return redirect("/admin_dashboard")

    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect("/admin_login")

    return render_template("admin_dashboard.html")
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/home")
@app.route("/admin/accounts")
def view_all_accounts():

    if "admin" not in session:
        return redirect("/admin_login")

    cursor.execute("""
    SELECT account_number, first_name, last_name, balance, account_status
    FROM accounts
    """)

    accounts = cursor.fetchall()

    return render_template("view_accounts.html", accounts=accounts)

@app.route("/admin/transactions")
def view_all_transactions():

    if "admin" not in session:
        return redirect("/admin_login")

    cursor.execute("""
    SELECT 
        accounts.first_name,
        accounts.last_name,
        transactions.account_number,
        transactions.txn_type,
        transactions.amount,
        transactions.date
    FROM transactions
    JOIN accounts
    ON transactions.account_number = accounts.account_number
    ORDER BY transactions.txn_id DESC
    """)

    txns = cursor.fetchall()

    return render_template("transactions.html", txns=txns)
from flask import jsonify, flash, redirect, render_template, request, session
@app.route("/admin/card_requests")
def admin_card_requests():
    if "admin" not in session:
        return redirect("/admin_login")
    cursor.execute("SELECT * FROM card_requests WHERE status='Pending'")
    data = cursor.fetchall()
    return render_template("card_requests.html", requests=data, page_type="pending")


@app.route("/admin/approved_cards")
def approved_cards():
    if "admin" not in session:
        return redirect("/admin_login")
    cursor.execute("SELECT * FROM card_requests WHERE status='Approved'")
    data = cursor.fetchall()
    return render_template("card_requests.html", requests=data, page_type="approved")


@app.route("/admin/rejected_cards")
def rejected_cards():
    if "admin" not in session:
        return redirect("/admin_login")
    cursor.execute("SELECT * FROM card_requests WHERE status='Rejected'")
    data = cursor.fetchall()
    return render_template("card_requests.html", requests=data, page_type="rejected")
@app.route("/admin/approve_card/<int:req_id>", methods=["GET", "POST"])
def approve_card(req_id):

    if "admin" not in session:
        return redirect("/admin_login")

    # Block GET requests
    if request.method == "GET":
        return redirect("/admin/card_requests")

    # Fetch request
    cursor.execute("""
    SELECT account_number, variant FROM card_requests WHERE request_id=?
    """, (req_id,))
    data = cursor.fetchone()

    if not data:
        flash("Request not found", "danger")
        return redirect("/admin/card_requests")

    acc_no, variant = data

    # Already has card
    cursor.execute("SELECT 1 FROM debit_cards WHERE account_number=?", (acc_no,))
    if cursor.fetchone():
        flash("Debit card already exists for this account", "warning")
        return redirect("/admin/card_requests")

    network = variant.split()[0]

    try:
        card_number = generate_card_number(network)
        expiry = generate_expiry()

        # ✅ FIXED: No cvv column, correct 7 values matching 7 columns
        cursor.execute("""
        INSERT INTO debit_cards(
            card_number, account_number, network, variant,
            expiry_date, card_pin, issue_date
        )
        VALUES(?,?,?,?,?,?,?)
        """, (card_number, acc_no, network, variant,
              expiry, "", datetime.now().isoformat()))

        # Update request status
        cursor.execute("""
        UPDATE card_requests 
        SET status='Approved'
        WHERE request_id=?
        """, (req_id,))

        conn.commit()

        # Send email to user
        cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
        email_data = cursor.fetchone()
        if email_data:
            try:
                send_simple_email(email_data[0],
                    "✅ Your debit card request has been approved! Your card is now active.")
            except:
                pass

        flash("Debit card approved successfully ✅", "success")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR:", e)
        flash("Something went wrong while approving card", "danger")

    return redirect("/admin/card_requests")

@app.route("/admin/reject_card/<int:req_id>", methods=["GET", "POST"])
def reject_card(req_id):

    if "admin" not in session:
        return redirect("/admin_login")

    # ✅ FIX 1: Block GET requests — reject must only happen via POST form
    if request.method == "GET":
        return redirect("/admin/card_requests")

    # Fetch request
    cursor.execute("""
    SELECT account_number FROM card_requests WHERE request_id=?
    """, (req_id,))
    data = cursor.fetchone()

    if not data:
        flash("Request not found", "danger")
        return redirect("/admin/card_requests")

    acc_no = data[0]

    try:
        # Update status to Rejected
        cursor.execute("""
        UPDATE card_requests
        SET status='Rejected',
            rejection_count = rejection_count + 1,
            request_time = ?
        WHERE request_id=?
        """, (datetime.now().isoformat(), req_id))

        conn.commit()

        # Send email to user
        cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
        email_data = cursor.fetchone()

        if email_data:
            try:
                send_simple_email(
                    email_data[0],
                    "❌ Your debit card request has been rejected. You can reapply after 24 hours."
                )
            except:
                pass

        flash("Debit card request rejected ❌", "warning")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR:", e)
        flash("Something went wrong while rejecting request", "danger")

    # ✅ FIX 2: Redirect back to card requests page, not admin dashboard
    return redirect("/admin/card_requests")

# ==============================
# LOCK / UNLOCK ACCOUNT
# ==============================

@app.route("/admin/lock_account", methods=["GET","POST"])
def lock_account():

    if "admin" not in session:
        return redirect("/admin_login")

    if request.method == "POST":

        acc_no = request.form["account"]
        action = request.form["action"]

        cursor.execute(
        "SELECT account_status FROM accounts WHERE account_number=?",
        (acc_no,)
        )

        data = cursor.fetchone()

        if not data:
            flash("Account not found", "danger")
            return redirect("/admin/lock_account")

        status = data[0]

        if status == "Closed":
            flash("This account is already closed.", "danger")
            return redirect("/admin/lock_account")

        # 🔒 LOCK
        if action == "lock":

            lock_time = datetime.now() + timedelta(hours=12)

            cursor.execute("""
            UPDATE accounts 
            SET account_status='Locked', lock_until=?
            WHERE account_number=?
            """, (lock_time.isoformat(), acc_no))

            flash("Account locked successfully for 12 hours", "success")

        # 🔓 UNLOCK
        elif action == "unlock":

            cursor.execute("""
            UPDATE accounts
            SET account_status='Active', login_attempts=0, lock_until=NULL
            WHERE account_number=?
            """, (acc_no,))

            flash("Account unlocked successfully", "success")

        conn.commit()

        return redirect("/admin/lock_account")

    return render_template("lock_account.html")


# ==============================
# LIVE ACCOUNT NAME CHECK
# ==============================

@app.route("/get_account/<acc>")
def get_account(acc):

    cursor.execute(
    "SELECT first_name, last_name, account_status FROM accounts WHERE account_number=?",
    (acc,)
    )

    data = cursor.fetchone()

    if not data:
        return jsonify({"name": "Account not found"})

    first, last, status = data

    return jsonify({
        "name": f"{first} {last}",
        "status": status
    })

@app.route("/admin/statistics")
def bank_statistics():

    if "admin" not in session:
        return redirect("/admin_login")

    cursor.execute("SELECT COUNT(*) FROM accounts")
    total_accounts = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(balance) FROM accounts")
    total_money = cursor.fetchone()[0]

    if total_money is None:
        total_money = 0

    cursor.execute("SELECT COUNT(*) FROM loans WHERE loan_status='Approved'")
    total_loans = cursor.fetchone()[0]

    return render_template(
        "statistics.html",
        total_accounts=total_accounts,
        total_money=total_money,
        total_loans=total_loans
    )
@app.route("/admin/search_account", methods=["GET","POST"])
def search_account():

    if "admin" not in session:
        return redirect("/admin_login")

    account = None
    error = None
    loan_status = "No Loan"

    if request.method == "POST":

        acc_no = request.form["account"]

        cursor.execute("""
        SELECT 
        account_number,
        first_name,
        last_name,
        balance,
        account_status,
        cif_number,
        account_creation_date,
        father_name
        FROM accounts
        WHERE account_number=?
        """,(acc_no,))

        account = cursor.fetchone()

        if account:

            # check loan
            cursor.execute("""
            SELECT loan_status
            FROM loans
            WHERE account_number=? AND loan_status='Approved'
            """,(acc_no,))

            loan = cursor.fetchone()

            if loan:
                loan_status = "Loan Active"

        else:
            error = "Account not found"

    return render_template(
        "search_account.html",
        account=account,
        loan_status=loan_status,
        error=error
    )


# 
@app.route("/change_mpin", methods=["GET","POST"])
def change_mpin():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    if request.method == "POST":

        cif = request.form.get("cif")
        old_mpin = request.form.get("old_mpin")
        new_mpin = request.form.get("new_mpin")
        confirm_mpin = request.form.get("confirm_mpin")

        cursor.execute(
        "SELECT cif_number, mpin, email FROM accounts WHERE account_number=?",
        (acc_no,)
        )

        data = cursor.fetchone()

        if not data:
            flash("Account not found", "danger")
            return redirect("/change_mpin")

        stored_cif, stored_mpin, email = data

        if cif != stored_cif:
            flash("Invalid CIF number", "danger")
            return redirect("/change_mpin")

        if hash_text(old_mpin) != stored_mpin:
            flash("Old MPIN incorrect", "danger")
            return redirect("/change_mpin")

        if new_mpin != confirm_mpin:
            flash("MPIN mismatch", "danger")
            return redirect("/change_mpin")

        if not new_mpin.isdigit() or len(new_mpin) != 6:
            flash("MPIN must be 6 digits", "danger")
            return redirect("/change_mpin")

        # ✅ SAVE TEMP DATA
        session["mpin_change_temp"] = {
            "new_mpin": hash_text(new_mpin)
        }

        # ✅ SEND OTP
        send_otp(email)

        flash("OTP sent to your email", "info")
        return redirect("/verify_mpin_otp")

    return render_template("change_mpin.html")

@app.route("/verify_mpin_otp", methods=["GET","POST"])
def verify_mpin_otp():

    if "mpin_change_temp" not in session:
        return redirect("/dashboard")

    if request.method == "POST":

        entered_otp = request.form.get("otp")

        expiry = datetime.fromisoformat(session.get("otp_expiry"))

        if datetime.now() > expiry:
            flash("OTP expired", "danger")
            return redirect("/change_mpin")

        session["otp_attempts"] = session.get("otp_attempts", 0) + 1

        if session["otp_attempts"] > 3:
            flash("Too many wrong attempts", "danger")
            return redirect("/change_mpin")

        if entered_otp != session.get("otp"):
            flash("Invalid OTP", "danger")
            return redirect("/verify_mpin_otp")

        # ✅ OTP SUCCESS
        acc_no = session["account"]
        new_mpin = session["mpin_change_temp"]["new_mpin"]

        # 🔥 GET current count + email
        cursor.execute("""
        SELECT email, mpin_change_count, mpin_change_time
        FROM accounts
        WHERE account_number=?
        """,(acc_no,))

        data = cursor.fetchone()

        email, count, last_time = data

        now = datetime.now()

        # 🔥 LIMIT CHECK AGAIN (extra safety)
        if last_time:
            last_time = datetime.fromisoformat(last_time)

            if now - last_time < timedelta(hours=24):
                if count >= 2:
                    flash("MPIN change limit reached (2 times in 24 hours)", "danger")
                    return redirect("/dashboard")
            else:
                count = 0

        try:

            # ✅ UPDATE MPIN + COUNT + TIME
            cursor.execute("""
            UPDATE accounts
            SET mpin=?,
                mpin_change_count = COALESCE(mpin_change_count,0) + 1,
                mpin_change_time = ?
            WHERE account_number=?
            """,(new_mpin, now.isoformat(), acc_no))

            conn.commit()

            # ✅ SEND ALERT EMAIL
            send_mpin_change_alert(email)

        except Exception as e:
            conn.rollback()
            print("Error:", e)
            flash("MPIN update failed", "danger")
            return redirect("/change_mpin")

        # ✅ CLEAR SESSION
        session.pop("mpin_change_temp", None)
        session.pop("otp", None)
        session.pop("otp_expiry", None)
        session.pop("otp_attempts", None)

        flash("MPIN changed successfully", "success")
        return redirect("/dashboard")

    return render_template("verify_otp.html")

# @app.route("/approve_loan/<int:loan_id>")
# def approve_loan(loan_id):

#     if "admin" not in session:
#         return redirect("/admin_login")

#     cursor.execute("""
#     UPDATE loans
#     SET loan_status='Approved'
#     WHERE loan_id=?
#     """,(loan_id,))

#     conn.commit()

#     return redirect("/admin/loans")


@app.route("/approve_loan/<int:loan_id>")
def approve_loan(loan_id):

    if "admin" not in session:
        return redirect("/admin_login")

    # 🔥 Get loan details
    cursor.execute("""
    SELECT account_number, loan_amount
    FROM loans
    WHERE loan_id=?
    """,(loan_id,))

    loan = cursor.fetchone()

    if not loan:
        flash("Loan not found", "danger")
        return redirect("/admin/loans")

    acc_no = loan["account_number"]
    amount = loan["loan_amount"]

    try:
        # ✅ Update loan status
        cursor.execute("""
        UPDATE loans
        SET loan_status='Approved',
            approved_date=?
        WHERE loan_id=?
        """,(datetime.now(), loan_id))

        # ✅ ADD MONEY TO USER ACCOUNT
        cursor.execute("""
        UPDATE accounts
        SET balance = balance + ?
        WHERE account_number=?
        """,(amount, acc_no))

        # ✅ Record transaction
        cursor.execute("""
        INSERT INTO transactions(account_number, txn_type, amount, date)
        VALUES(?,?,?,?)
        """,(acc_no, "Loan Credit", amount, datetime.now()))

        # loan approve + balance add ho gaya...

        cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
        email = cursor.fetchone()[0]

        send_loan_status_email(email, amount, "Approved")

        conn.commit()

        flash("Loan approved and amount credited successfully", "success")

    except:
        conn.rollback()
        flash("Error while approving loan", "danger")

    return redirect("/admin/loans")
@app.route("/admin/approved_loans")
def approved_loans():

    if "admin" not in session:
        return redirect("/admin_login")

    cursor.execute("""
    SELECT loans.account_number,
           accounts.first_name,
           accounts.last_name,
           loans.loan_amount,
           loans.approved_date
    FROM loans
    JOIN accounts
    ON loans.account_number = accounts.account_number
    WHERE loans.loan_status='Approved'
    """)

    loans = cursor.fetchall()

    return render_template("approved_loans.html", loans=loans)
@app.route("/admin/reject_loan/<int:loan_id>")
def reject_loan(loan_id):

    if "admin" not in session:
        return redirect("/admin_login")

    cursor.execute("""
    UPDATE loans
    SET loan_status='Rejected'
    WHERE loan_id=?
    """,(loan_id,))

    cursor.execute("SELECT account_number, loan_amount FROM loans WHERE loan_id=?", (loan_id,))
    data = cursor.fetchone()

    if not data:
        flash("Loan not found", "danger")
        return redirect("/admin/loans")

    acc_no = data["account_number"]
    amount = data["loan_amount"]

    cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
    email = cursor.fetchone()[0]

    send_loan_status_email(email, amount, "Rejected")

    conn.commit()

    return redirect("/admin/loans")
@app.route("/admin/loans")
def view_loan_requests():

    if "admin" not in session:
        return redirect("/admin_login")

    cursor.execute("""
    SELECT loan_id, account_number, loan_amount,loan_date
    FROM loans
    WHERE loan_status='Pending'
    """)

    loans = cursor.fetchall()

    return render_template("loans.html", loans=loans)


@app.route("/get_receiver/<acc_no>")
def get_receiver(acc_no):

    cursor.execute("""
    SELECT first_name,last_name
    FROM accounts
    WHERE account_number=?
    """,(acc_no,))

    data = cursor.fetchone()

    if data:
        return {"name": data[0] + " " + data[1]}
    else:
        return {"name": "Account not found"}

@app.route("/transfer", methods=["GET","POST"])
def transfer_money():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    # 🔥 FIX: handle both POST and OTP-return GET
    if request.method == "POST" or "transfer_verified" in session:

        # 🔥 use session data after OTP
        if "transfer_verified" in session and "transfer_temp" in session:
            data = session["transfer_temp"]
            receiver = data["receiver"]
            mpin = data["mpin"]
            amount = data["amount"]
        else:
            receiver = request.form["receiver"].strip()
            mpin = request.form["mpin"].strip()
            amount = float(request.form["amount"])

        # ===== OTP CHECK =====
        if "transfer_verified" not in session:

            cursor.execute(
                "SELECT email FROM accounts WHERE account_number=?",
                (acc_no,)
            )
            email = cursor.fetchone()[0]

            # Save form data
            session["transfer_temp"] = {
                "receiver": receiver,
                "mpin": mpin,
                "amount": amount
            }

            send_otp(email)

            flash("OTP sent to your email")
            return redirect("/verify_transfer_otp")

        # ===== ACTUAL TRANSFER =====

        if receiver == acc_no:
            flash("Cannot transfer to your own account", "danger")
            return redirect("/transfer")

        if amount > 50000:
            return "Transfer limit exceeded (Max ₹50000)"

        cursor.execute(
        "SELECT first_name,last_name FROM accounts WHERE account_number=?",
        (receiver,)
        )
        receiver_data = cursor.fetchone()

        if not receiver_data:
            flash("Receiver account not found", "danger")
            return redirect("/transfer")

        receiver_name = receiver_data[0] + " " + receiver_data[1]

        cursor.execute(
        "SELECT mpin,balance,account_status FROM accounts WHERE account_number=?",
        (acc_no,)
        )
        result = cursor.fetchone()

        if not result:
            return "Sender account not found"

        stored_mpin, balance, status = result

        if status != "Active":
            return "Account is not active"

        if hash_text(mpin) != stored_mpin:
            flash("Wrong MPIN", "danger")
            return redirect("/transfer")

        if amount <= 0:
            return "Invalid amount"

        if amount > balance:
            flash("Insufficient balance", "danger")
            return redirect("/transfer")

        try:
            cursor.execute(
            "UPDATE accounts SET balance=balance-? WHERE account_number=?",
            (amount, acc_no)
            )

            cursor.execute(
            "UPDATE accounts SET balance=balance+? WHERE account_number=?",
            (amount, receiver)
            )

            cursor.execute("""
            INSERT INTO transactions(account_number,txn_type,amount,date)
            VALUES(?,?,?,?)
            """,(acc_no,"Transfer Sent",amount,datetime.now()))

            cursor.execute("""
            INSERT INTO transactions(account_number,txn_type,amount,date)
            VALUES(?,?,?,?)
            """,(receiver,"Transfer Received",amount,datetime.now()))

            conn.commit()

            # 🔥 CLEAR SESSION
            session.pop("transfer_verified", None)
            session.pop("transfer_temp", None)
            session.pop("otp", None)

            flash(f"₹{amount} transferred successfully to {receiver_name}")
            return redirect("/dashboard")

        except:
            conn.rollback()
            flash ("Transaction failed", "danger")
            return redirect("/transfer")

    return render_template("transfer.html")
@app.route("/verify_transfer_otp", methods=["GET","POST"])
def verify_transfer_otp():

    if "transfer_temp" not in session:
        return redirect("/dashboard")

    if request.method == "POST":

        entered_otp = request.form["otp"]

        expiry = datetime.fromisoformat(session.get("otp_expiry"))

        if datetime.now() > expiry:
            flash("OTP expired")
            return redirect("/transfer")

        # attempt limit
        session["otp_attempts"] = session.get("otp_attempts", 0) + 1

        if session["otp_attempts"] > 3:
            flash("Too many wrong attempts")
            return redirect("/transfer")

        if entered_otp != session.get("otp"):
            flash("Invalid OTP")
            return redirect("/verify_transfer_otp")

        # ✅ OTP SUCCESS
        session["transfer_verified"] = True

        return redirect("/transfer")

    return render_template("verify_otp.html")

    

@app.route("/passbook")
def view_passbook():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    cursor.execute("""
    SELECT account_number, cif_number, first_name, last_name,
           father_name, dob, address, mobile,
           nominee_name, nominee_relation, balance, account_creation_date
    FROM accounts
    WHERE account_number=?
    """,(acc_no,))

    data = cursor.fetchone()

    if not data:
        flash("Account not found","danger")
        return redirect("/dashboard")

    return render_template("passbook.html", data=data)
    
@app.route("/mini_statement")
def mini_statement():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    cursor.execute("""
    SELECT txn_type, amount, date
    FROM transactions
    WHERE account_number=?
    ORDER BY txn_id DESC
    LIMIT 5
    """,(acc_no,))

    records = cursor.fetchall()

    formatted = []

    for r in records:
        try:
          dt = datetime.strptime(r[2], "%Y-%m-%d %H:%M:%S.%f")
        except:
          dt = datetime.strptime(r[2], "%Y-%m-%d %H:%M:%S")
        formatted_date = dt.strftime("%d %b %Y | %I:%M %p")
        formatted.append((r[0], r[1], formatted_date))

    return render_template("mini_statement.html", records=formatted)
@app.route("/close_account", methods=["GET","POST"])
def close_account():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    if request.method == "POST":

        mpin = request.form["mpin"]

        cursor.execute("""
        SELECT mpin, balance, account_status
        FROM accounts
        WHERE account_number=?
        """,(acc_no,))

        data = cursor.fetchone()

        if not data:
            flash("Account not found","danger")
            return redirect("/dashboard")

        stored_mpin, balance, status = data

        if status != "Active":
            flash("Account already closed","danger")
            return redirect("/dashboard")

        if hash_text(mpin) != stored_mpin:
            flash("Wrong MPIN","danger")
            return redirect("/close_account")

        if balance != 0:
            flash("Balance must be zero before closing account","danger")
            return redirect("/dashboard")

        # Check if loan exists
        cursor.execute("""
        SELECT loan_status
        FROM loans
        WHERE account_number=? AND loan_status!='Closed'
        """,(acc_no,))

        loan = cursor.fetchone()

        if loan:
            flash("Account cannot be closed until loan is fully repaid","danger")
            return redirect("/dashboard")

        # Close account
        cursor.execute("""
        UPDATE accounts
        SET account_status='Closed'
        WHERE account_number=?
        """,(acc_no,))

        conn.commit()

        session.clear()

        flash("Account closed successfully","success")

        return redirect("/home")

    return render_template("close_account.html")
@app.route("/apply_loan", methods=["GET","POST"])
def apply_loan():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    cursor.execute(
        "SELECT balance, email FROM accounts WHERE account_number=?",
        (acc_no,)
    )

    result = cursor.fetchone()

    if not result:
        flash("Account not found","danger")
        return redirect("/dashboard")

    balance, email = result   # 🔥 email add kiya

    # Minimum balance condition
    if balance < 5000:
        flash("Minimum balance ₹5000 required to apply for loan","danger")
        return redirect("/dashboard")

    # Check if loan already exists
    cursor.execute("""
    SELECT loan_status
    FROM loans
    WHERE account_number=? AND loan_status!='Closed'
    """,(acc_no,))

    existing_loan = cursor.fetchone()

    if existing_loan:
        flash("You already have a pending or active loan","danger")
        return redirect("/dashboard")

    max_loan = balance * 3

    if request.method == "POST":

        try:
            amount = float(request.form["amount"])
        except:
            flash("Invalid loan amount","danger")
            return redirect("/apply_loan")

        if amount <= 0:
            flash("Loan amount must be greater than 0","danger")
            return redirect("/apply_loan")

        if amount > max_loan:
            flash(f"Loan exceeds eligibility (Max ₹{max_loan})","danger")
            return redirect("/apply_loan")

        # 🔥 ONLY ADD THIS PART (OTP STEP)
        session["loan_temp"] = {
            "amount": amount
        }

        send_otp(email)

        flash("OTP sent to your email","info")
        return redirect("/verify_loan_otp")

    return render_template("apply_loan.html", max_loan=max_loan)
@app.route("/verify_loan_otp", methods=["GET","POST"])
def verify_loan_otp():

    if "loan_temp" not in session:
        return redirect("/dashboard")

    if request.method == "POST":

        entered_otp = request.form["otp"]

        expiry = datetime.fromisoformat(session.get("otp_expiry"))

        if datetime.now() > expiry:
            flash("OTP expired","danger")
            return redirect("/apply_loan")

        if entered_otp != session.get("otp"):
            flash("Invalid OTP","danger")
            return redirect("/verify_loan_otp")

        # ✅ OTP SUCCESS
        acc_no = session["account"]
        amount = session["loan_temp"]["amount"]

        try:
            # ✅ INSERT LOAN
            cursor.execute("""
            INSERT INTO loans(account_number, loan_amount, interest_rate, loan_date, loan_status)
            VALUES(?,?,?,?,?)
            """,(acc_no, amount, 10.5, datetime.now(), "Pending"))

            conn.commit()

            # 🔥 EMAIL PART ADD
            cursor.execute("SELECT email FROM accounts WHERE account_number=?", (acc_no,))
            data = cursor.fetchone()

            if data and data[0]:
                send_loan_request_email(data[0], amount)
                print("✅ Loan request email sent")
            else:
                print("❌ Email not found")

        except Exception as e:
            conn.rollback()
            print("❌ ERROR:", e)
            flash("Loan request failed","danger")
            return redirect("/apply_loan")

        # ✅ CLEANUP
        session.pop("loan_temp", None)
        session.pop("otp", None)
        session.pop("otp_expiry", None)

        flash("Loan request submitted successfully","success")
        return redirect("/dashboard")

    return render_template("verify_otp.html")
@app.route("/loan_status")
def view_loan_status():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    cursor.execute("""
    SELECT loan_id, loan_amount, interest_rate, loan_status
    FROM loans
    WHERE account_number=?
    """,(acc_no,))

    loans = cursor.fetchall()

    return render_template("loan_status.html", loans=loans)

# ==============================
# USER DASHBOARD
# ==============================


@app.route("/dashboard")
def dashboard():

    if "account" not in session:
        return redirect("/user_login")

    acc_no = session["account"]

    # USER DETAILS
    cursor.execute("""
    SELECT first_name, last_name, balance
    FROM accounts WHERE account_number=?
    """, (acc_no,))

    data = cursor.fetchone()
    name = data[0] + " " + data[1]
    balance = data[2]

    # DEFAULT VALUES
    has_card = False
    card_status = "Not Applied"
    card_last4 = None
    expiry = None
    network = None
    can_reapply = False

    # CHECK ACTIVE CARD
    cursor.execute("""
    SELECT card_number, variant, expiry_date
    FROM debit_cards WHERE account_number=?
    """, (acc_no,))

    card = cursor.fetchone()

    if card:
        has_card = True
        card_status = "Active"
        card_last4 = card[0][-4:]
        expiry = card[2]
        network = card[1].split()[0]

    else:
        # CHECK REQUEST STATUS
        cursor.execute("""
        SELECT status, request_time FROM card_requests
        WHERE account_number=?
        ORDER BY request_id DESC LIMIT 1
        """, (acc_no,))

        req = cursor.fetchone()

        if req:
            status, request_time = req

            if status == "Pending":
                # ✅ FIX 1: meaningful label
                card_status = "Applied for Debit Card"

            elif status == "Approved":
                # approved but card not yet in debit_cards table edge case
                card_status = "Applied for Debit Card"

            elif status == "Rejected":
                # ✅ FIX 2: check if 24 hours have passed
                if request_time:
                    rejection_time = datetime.fromisoformat(request_time)
                    if datetime.now() > rejection_time + timedelta(hours=24):
                        # 24 hours passed — reset to Not Applied
                        card_status = "Not Applied"
                        can_reapply = True
                    else:
                        card_status = "Rejected"
                        can_reapply = False
                else:
                    card_status = "Rejected"

    return render_template(
        "dashboard.html",
        balance=balance,
        name=name,
        acc_no=acc_no,
        has_card=has_card,
        card_status=card_status,
        card_last4=card_last4,
        expiry=expiry,
        network=network,
        can_reapply=can_reapply
    )

# ==============================
# MAIN MENU
# ==============================


if __name__ == "__main__":
    app.run(debug=True,use_reloader=False)




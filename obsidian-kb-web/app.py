import os
from functools import wraps
from flask import Flask, request, redirect, url_for, session, send_from_directory

SITE_DIR = os.path.join(os.path.dirname(__file__), "site")

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "change-me")

USERNAME = os.environ.get("KB_USERNAME", "daniel")
PASSWORD = os.environ.get("KB_PASSWORD")

if not PASSWORD:
    raise RuntimeError("KB_PASSWORD env var is required")

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("authed"):
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper

@app.route('/login', methods=['GET', 'POST'])
def login():
    err = ""
    if request.method == 'POST':
        user = request.form.get('username', '')
        pw = request.form.get('password', '')
        if user == USERNAME and pw == PASSWORD:
            session['authed'] = True
            return redirect(request.args.get('next') or url_for('root'))
        err = "Invalid credentials"
    return f'''<!doctype html><html><body style="font-family:sans-serif;max-width:420px;margin:5rem auto;">
    <h2>Obsidian KB Login</h2><p>Private access</p>
    <form method="post"><label>Username</label><br><input name="username" style="width:100%;padding:8px"><br><br>
    <label>Password</label><br><input name="password" type="password" style="width:100%;padding:8px"><br><br>
    <button type="submit">Sign in</button></form>
    <p style="color:#b00">{err}</p></body></html>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', defaults={'path': 'index.html'})
@app.route('/<path:path>')
@login_required
def root(path):
    full = os.path.join(SITE_DIR, path)
    if os.path.isdir(full):
        path = os.path.join(path, 'index.html')
    if os.path.exists(os.path.join(SITE_DIR, path)):
        return send_from_directory(SITE_DIR, path)
    return send_from_directory(SITE_DIR, '404.html'), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

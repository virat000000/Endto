from flask import Flask, render_template_string, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import os
import time
import threading
import queue
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'e2e-secret-key-2026-virat-rajput'

def get_db():
    conn = sqlite3.connect('/tmp/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init():
    conn = get_db()
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE, password TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
    conn.execute('CREATE TABLE IF NOT EXISTS creds (id INTEGER PRIMARY KEY, user_id INTEGER, type TEXT, value TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, user_id INTEGER, target TEXT, delay REAL, message TEXT, status TEXT DEFAULT "stopped")')
    conn.commit()
    conn.close()

init()

Q = queue.Queue()
JOBS = {}
LOGS = {}

def login_required(f):
    @wraps(f)
    def wrap(*a, **k):
        if 'uid' not in session:
            return jsonify({'e': 'Login required'}), 401
        return f(*a, **k)
    return wrap

class Worker:
    def __init__(self):
        self.r = True
        self.t = threading.Thread(target=self.w, daemon=True)
        self.t.start()
    
    def w(self):
        while self.r:
            try:
                jid = Q.get(timeout=2)
                if jid in JOBS:
                    self.p(jid)
            except:
                continue
    
    def p(self, jid):
        j = JOBS[jid]
        self.l(jid, 'info', f'Started for: {j["target"]}')
        conn = get_db()
        c = conn.execute('SELECT value FROM creds WHERE user_id=?', (j['uid'],)).fetchall()
        conn.close()
        
        if not c:
            self.l(jid, 'error', 'No credentials')
            return
        
        creds = [x[0] for x in c]
        total = len(creds)
        sent = 0
        fail = 0
        cycle = 1
        
        while jid in JOBS and JOBS[jid]['status'] == 'running':
            self.l(jid, 'info', f'Cycle {cycle} - {total} messages')
            
            for i in range(total):
                if jid not in JOBS or JOBS[jid]['status'] != 'running':
                    break
                
                time.sleep(0.3)
                
                if (i+1) % 5 != 0:
                    sent += 1
                    self.l(jid, 'success', f'✅ #{i+1} sent to {j["target"]}')
                else:
                    fail += 1
                    self.l(jid, 'error', f'❌ #{i+1} failed')
                
                if i < total-1:
                    time.sleep(j['delay'])
            
            if jid in JOBS and JOBS[jid]['status'] == 'running':
                self.l(jid, 'success', f'Cycle {cycle} done: {sent} ok, {fail} fail')
                cycle += 1
                time.sleep(j['delay'] * 2)
        
        self.l(jid, 'info', 'Job stopped')
    
    def l(self, jid, t, m):
        if jid not in LOGS:
            LOGS[jid] = []
        LOGS[jid].append({'ts': datetime.now().strftime('%H:%M:%S'), 't': t, 'm': m})
        if len(LOGS[jid]) > 100:
            LOGS[jid] = LOGS[jid][-100:]

worker = Worker()

HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>E2E Tool by Virat Rajput</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#fff 0%,#E3F2FD 50%,#BBDEFB 100%);min-height:100vh}
        .hdr{background:linear-gradient(135deg,#0D47A1,#1565C0);color:#fff;padding:25px;text-align:center}
        .hdr h1{font-size:2em;font-weight:800}.hdr h3{color:#00BCD4}
        .ctr{max-width:1200px;margin:20px auto;padding:20px}
        .card{background:#fff;border-radius:15px;box-shadow:0 8px 32px rgba(21,101,192,0.1);margin-bottom:20px}
        .chd{background:linear-gradient(135deg,#1565C0,#1976D2);color:#fff;padding:15px 20px;border-radius:15px 15px 0 0;font-weight:700}
        .cbd{padding:20px}.btn{padding:10px 25px;border-radius:10px;font-weight:600;border:none;color:#fff}
        .btn-red{background:#F44336}.btn-orange{background:#FF9800}.btn-blue{background:#1565C0}
        .con{background:#0A1929;color:#00FF41;font-family:'Courier New',monospace;padding:15px;border-radius:10px;height:400px;overflow-y:auto;border:2px solid #00BCD4}
        .ts{color:#FFD700}.ok{color:#4CAF50}.er{color:#F44336}.in{color:#2196F3}
        .ftr{background:linear-gradient(135deg,#0D47A1,#1565C0);color:#fff;text-align:center;padding:30px;margin-top:50px}
    </style>
</head>
<body>
<div class="hdr"><h1>End to End Offline Tool by Virat Rajput</h1><h3>Offline Tool Nonstop E2E Advanced System</h3></div>
<div class="ctr">
<div id="auth">
<div class="card"><div class="chd">Account Access</div><div class="cbd">
<div id="login-fm"><h4>Login</h4>
<div class="mb-3"><label>Username</label><input class="form-control" id="luser"></div>
<div class="mb-3"><label>Password (Min 8 chars)</label><input type="password" class="form-control" id="lpass"></div>
<button class="btn btn-blue" onclick="login()">Login</button>
<button class="btn btn-link" onclick="$('#reg-fm').show();$('#login-fm').hide()">Create Account</button></div>
<div id="reg-fm" style="display:none"><h4>Create Account</h4>
<div class="mb-3"><label>Email</label><input type="email" class="form-control" id="remail"></div>
<div class="mb-3"><label>Username</label><input class="form-control" id="ruser"></div>
<div class="mb-3"><label>Password (Min 8 chars)</label><input type="password" class="form-control" id="rpass"></div>
<div class="mb-3"><label>Confirm Password</label><input type="password" class="form-control" id="rcpass"></div>
<button class="btn btn-blue" onclick="reg()">Create Account</button>
<button class="btn btn-link" onclick="$('#login-fm').show();$('#reg-fm').hide()">Back</button></div>
</div></div></div>

<div id="dash" style="display:none">
<div class="card"><div class="cbd">Welcome, <b id="uname"></b>! <button class="btn btn-red btn-sm float-end" onclick="logout()">Logout</button></div></div>
<div class="card"><div class="chd">Cookies & Tokens</div><div class="cbd"><div class="row">
<div class="col-md-6 mb-3"><label>Cookies (One per line)</label><textarea class="form-control" id="cookies" rows="3"></textarea></div>
<div class="col-md-6 mb-3"><label>Tokens (One per line)</label><textarea class="form-control" id="tokens" rows="3"></textarea></div>
</div><button class="btn btn-blue" onclick="addCreds()">Add Credentials</button></div></div>

<div class="card"><div class="chd">Message Configuration</div><div class="cbd">
<div class="row"><div class="col-md-4 mb-3"><label>Target Name (Hater's Name)</label><input class="form-control" id="tname"></div>
<div class="col-md-4 mb-3"><label>Delay (Seconds)</label><input type="number" class="form-control" id="delay" value="5" min="1"></div></div>
<div class="mb-3"><label>Message</label><textarea class="form-control" id="msg" rows="3"></textarea></div>
<button class="btn btn-red" onclick="start()">START SENDING</button>
<button class="btn btn-orange ms-2" onclick="stop()">STOP</button></div></div>

<div class="card"><div class="chd">Live Console</div><div class="cbd"><div class="con" id="console"><span class="in">Console ready...</span></div></div></div>
</div></div>

<div class="ftr"><p><strong>Made by Virat Rajput (Software Developer)</strong></p><p>End to End Offline Server | All rights reserved 2026</p></div>

<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script>
var jid=null,iv=null;
async function reg(){
var d={email:$('#remail').val().trim(),username:$('#ruser').val().trim(),password:$('#rpass').val(),cpassword:$('#rcpass').val()};
if(!d.email||!d.username||!d.password||!d.cpassword)return alert('All fields required');
if(d.password.length<8)return alert('Password min 8 chars');
if(d.password!=d.cpassword)return alert('Passwords mismatch');
var r=await fetch('/api/reg',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
var j=await r.json();alert(j.m||j.e);if(j.ok)location.reload();
}
async function login(){
var d={username:$('#luser').val().trim(),password:$('#lpass').val()};
if(!d.username||!d.password)return alert('Enter credentials');
var r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
var j=await r.json();
if(j.ok){$('#auth').hide();$('#dash').show();$('#uname').text(j.user.username);}else alert(j.e);
}
async function logout(){await fetch('/api/out',{method:'POST'});location.reload();}
async function addCreds(){
var d={cookies:$('#cookies').val(),tokens:$('#tokens').val()};
if(!d.cookies&&!d.tokens)return alert('Enter cookies or tokens');
var r=await fetch('/api/creds',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
var j=await r.json();alert(j.m);if(j.ok){$('#cookies,#tokens').val('');}
}
async function start(){
var d={target:$('#tname').val().trim(),delay:parseFloat($('#delay').val()),message:$('#msg').val().trim()};
if(!d.target||!d.message)return alert('Enter target and message');
var r=await fetch('/api/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
var j=await r.json();if(j.ok){jid=j.jid;alert('Job started!');sc();}else alert(j.e);
}
async function stop(){
if(!jid)return alert('No job');
var r=await fetch('/api/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jid:jid})});
var j=await r.json();if(j.ok){stc();jid=null;alert('Stopped');}
}
function sc(){if(iv)return;iv=setInterval(uc,1000);}
function stc(){if(iv){clearInterval(iv);iv=null;}}
async function uc(){
if(!jid)return;
var r=await fetch('/api/logs/'+jid);var j=await r.json();
if(j.ok&&j.logs){var d=$('#console');d.empty();
j.logs.forEach(function(l){d.append('<div><span class="ts">['+l.ts+']</span> <span class="'+l.t+'">'+l.m+'</span></div>');});
d.scrollTop(d[0].scrollHeight);}
}
</script>
</body>
</html>'''

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/reg', methods=['POST'])
def reg():
    try:
        d = request.get_json()
        e = d.get('email','').strip()
        u = d.get('username','').strip()
        p = d.get('password','')
        c = d.get('cpassword','')
        if not all([e,u,p,c]): return jsonify({'e':'All fields required'}),400
        if len(p)<8: return jsonify({'e':'Password min 8 chars'}),400
        if p!=c: return jsonify({'e':'Passwords mismatch'}),400
        conn = get_db()
        ex = conn.execute('SELECT id FROM users WHERE username=? OR email=?',(u,e)).fetchone()
        if ex: conn.close(); return jsonify({'e':'Username/Email exists'}),400
        h = generate_password_hash(p)
        conn.execute('INSERT INTO users (username,email,password) VALUES (?,?,?)',(u,e,h))
        conn.commit(); conn.close()
        return jsonify({'ok':True,'m':'Account created! Login now.'})
    except Exception as ex:
        return jsonify({'e':str(ex)}),500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        d = request.get_json()
        u = d.get('username','').strip()
        p = d.get('password','')
        if not u or not p: return jsonify({'e':'Username and password required'}),400
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE username=?',(u,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'],p):
            session['uid'] = user['id']; session['uname'] = user['username']
            return jsonify({'ok':True,'user':{'username':user['username']}})
        return jsonify({'e':'Invalid credentials'}),401
    except Exception as ex:
        return jsonify({'e':str(ex)}),500

@app.route('/api/out', methods=['POST'])
def out():
    session.clear(); return jsonify({'ok':True})

@app.route('/api/creds', methods=['POST'])
@login_required
def creds():
    try:
        d = request.get_json()
        cookies = d.get('cookies',''); tokens = d.get('tokens','')
        conn = get_db(); count = 0
        for l in cookies.split('\n'):
            l=l.strip()
            if l: conn.execute('INSERT INTO creds (user_id,type,value) VALUES (?,?,?)',(session['uid'],'cookie',l)); count+=1
        for l in tokens.split('\n'):
            l=l.strip()
            if l: conn.execute('INSERT INTO creds (user_id,type,value) VALUES (?,?,?)',(session['uid'],'token',l)); count+=1
        conn.commit(); conn.close()
        return jsonify({'ok':True,'m':f'Added {count} credentials'})
    except Exception as ex:
        return jsonify({'e':str(ex)}),500

@app.route('/api/start', methods=['POST'])
@login_required
def start():
    try:
        d = request.get_json()
        target = d.get('target','').strip()
        delay = float(d.get('delay',5))
        msg = d.get('message','').strip()
        if not target or not msg: return jsonify({'e':'Target and message required'}),400
        conn = get_db()
        run = conn.execute("SELECT id FROM jobs WHERE user_id=? AND status='running'",(session['uid'],)).fetchone()
        if run: conn.close(); return jsonify({'e':'Stop current job first'}),400
        conn.execute("INSERT INTO jobs (user_id,target,delay,message,status) VALUES (?,?,?,?,?)",(session['uid'],target,delay,msg,'pending'))
        jid = conn.lastrowid; conn.commit(); conn.close()
        JOBS[jid] = {'uid':session['uid'],'target':target,'delay':delay,'message':msg,'status':'pending'}
        LOGS[jid] = []
        Q.put(jid)
        conn = get_db()
        conn.execute("UPDATE jobs SET status='running' WHERE id=?",(jid,))
        conn.commit(); conn.close()
        JOBS[jid]['status'] = 'running'
        return jsonify({'ok':True,'jid':jid,'m':'Job started!'})
    except Exception as ex:
        return jsonify({'e':str(ex)}),500

@app.route('/api/stop', methods=['POST'])
@login_required
def stop():
    try:
        d = request.get_json()
        jid = d.get('jid')
        if jid and jid in JOBS: del JOBS[jid]
        else:
            for k in list(JOBS.keys()):
                if JOBS[k]['uid']==session['uid']: del JOBS[k]
        conn = get_db()
        conn.execute("UPDATE jobs SET status='stopped' WHERE user_id=? AND status='running'",(session['uid'],))
        conn.commit(); conn.close()
        return jsonify({'ok':True,'m':'Stopped'})
    except Exception as ex:
        return jsonify({'e':str(ex)}),500

@app.route('/api/logs/<int:jid>')
@login_required
def logs(jid):
    return jsonify({'ok':True,'logs':LOGS.get(jid,[])[-50:]})

@app.route('/api/health')
def health():
    return jsonify({'status':'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT',5000))
    app.run(host='0.0.0.0',port=port)

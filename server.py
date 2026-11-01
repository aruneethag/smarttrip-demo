"""SmartTrip demo server. SQLite transactions enforce ownership and revisions."""
import argparse
import hashlib
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from planner import Problem, DemoProvider, validate_details, revise, markdown, chat_reply, extract_intake, now

ROOT = Path(__file__).parent
DB_PATH = os.getenv('SMARTTRIP_DB', str(ROOT / 'data/smarttrip.sqlite3'))
SECURE = os.getenv('SECURE_COOKIES','0') == '1'
MAX_BODY = 32000

def default_host():
    return os.getenv('HOST') or ('0.0.0.0' if os.getenv('RENDER') == 'true' else '127.0.0.1')

def storage_policy():
    temporary = os.getenv('EPHEMERAL_STORAGE', '0') == '1'
    return {'temporary': temporary, 'notice': (
        'Temporary demo storage: saved trips can disappear when this hosted service sleeps, restarts, or redeploys. Download JSON or Markdown to keep a copy.'
        if temporary else '')}

@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        with db:
            yield db
    finally:
        db.close()

def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS trips(id TEXT PRIMARY KEY, session TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
          updated TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS results(session TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
          trip TEXT NOT NULL REFERENCES trips(id) ON DELETE CASCADE, scope TEXT NOT NULL, key TEXT NOT NULL,
          fingerprint TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(session,trip,scope,key));
        CREATE TABLE IF NOT EXISTS limits(bucket TEXT NOT NULL, window INTEGER NOT NULL, count INTEGER NOT NULL,
          PRIMARY KEY(bucket,window));
        ''')

def cleanup():
    cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
    with connect() as db:
        count=db.execute('DELETE FROM sessions WHERE updated < ?', (cutoff,)).rowcount
        db.execute('DELETE FROM limits WHERE window < ?', (int(time.time()//60)-2,))
    return count

class Handler(BaseHTTPRequestHandler):
    server_version='SmartTrip/1.0'
    def setup(self):
        super().setup()
        self.connection.settimeout(15)
    def log_message(self,*args):
        pass # Never log paths, trip details, cookies, or chat.

    def respond(self,status,data=None,content_type='application/json; charset=utf-8',headers=None):
        body = b'' if data is None else (json.dumps(data,ensure_ascii=False).encode() if content_type.startswith('application/json') else data.encode() if isinstance(data,str) else data)
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        for key,value in (headers or {}).items():
            self.send_header(key,value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self): self.handle_request()
    def do_POST(self): self.handle_request()
    def do_PATCH(self): self.handle_request()
    def do_DELETE(self): self.handle_request()

    def handle_request(self):
        try:
            self.route()
        except Problem as error:
            self.respond(error.status,{'error':{'code':error.code,'message':str(error),'fields':error.fields,'requestId':uuid.uuid4().hex}})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.respond(400,{'error':{'code':'BAD_JSON','message':'Send a valid JSON object.','fields':{},'requestId':uuid.uuid4().hex}})
        except Exception:
            self.respond(500,{'error':{'code':'INTERNAL_ERROR','message':'The request could not finish. Your last saved plan is preserved. Please retry.','fields':{},'requestId':uuid.uuid4().hex}})

    def read_body(self):
        try: length=int(self.headers.get('Content-Length','0'))
        except ValueError: raise Problem('Invalid request length.',400)
        if length<0 or length>MAX_BODY:
            raise Problem('Request is too large.',400)
        if length and not self.headers.get('Content-Type','').startswith('application/json'):
            raise Problem('Use application/json.',400)
        value=json.loads(self.rfile.read(length) or b'{}')
        if not isinstance(value,dict): raise Problem('Send a JSON object.',400)
        return value

    def session(self,db,create=False):
        cookie=SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: pass
        token=cookie.get('smarttrip_session')
        sid=hashlib.sha256(token.value.encode()).hexdigest() if token else ''
        row=db.execute('SELECT updated FROM sessions WHERE id=?',(sid,)).fetchone()
        cutoff=(datetime.now(timezone.utc)-timedelta(days=30)).isoformat()
        if row and row['updated'] < cutoff:
            db.execute('DELETE FROM sessions WHERE id=?',(sid,))
            row=None
        headers={}
        if not row:
            if not create: raise Problem('Your session has expired. Reload to start a new session.',401,code='SESSION_EXPIRED')
            token=secrets.token_urlsafe(32)
            sid=hashlib.sha256(token.encode()).hexdigest()
            db.execute('INSERT INTO sessions VALUES(?,?)',(sid,now()))
            headers['Set-Cookie']=f'smarttrip_session={token}; HttpOnly; SameSite=Strict; Path=/'+('; Secure' if SECURE else '')
        return sid,headers

    def route(self):
        path=urlparse(self.path).path
        method=self.command
        if not path.startswith('/api/'):
            files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
            if method!='GET' or path not in files:
                raise Problem('Page not found.',404,code='NOT_FOUND')
            f=ROOT/'static'/files[path]
            return self.respond(200,f.read_bytes(),{'html':'text/html','js':'text/javascript','css':'text/css'}[f.suffix[1:]]+'; charset=utf-8')
        if path=='/api/health' and method=='GET':
            with connect() as db:
                db.execute('SELECT 1 FROM sessions LIMIT 1').fetchone()
            return self.respond(200,{'status':'ok','mode':'demo','liveProviders':False,'storage':storage_policy()})
        if method!='GET':
            origin=self.headers.get('Origin')
            expected=('https' if SECURE else 'http')+'://'+self.headers.get('Host','')
            if origin != expected or self.headers.get('Sec-Fetch-Site')=='cross-site':
                raise Problem('Reload the app and try again from this site.',403,code='ORIGIN_REJECTED')
        payload=self.read_body() if method!='GET' else {}
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            sid,headers=self.session(db,create=path=='/api/session' and method=='POST')
            # Rate limiting stores only a one-way session hash and a minute bucket.
            if method!='GET':
                window=int(time.time()//60)
                db.execute('INSERT INTO limits VALUES(?,?,1) ON CONFLICT(bucket,window) DO UPDATE SET count=count+1',(sid,window))
                count=db.execute('SELECT count FROM limits WHERE bucket=? AND window=?',(sid,window)).fetchone()[0]
                if count>100: raise Problem('Too many requests. Please wait a minute.',429,code='RATE_LIMITED')
            if path=='/api/session':
                if method=='POST':
                    db.commit()
                    return self.respond(200,{'mode':'demo','retentionDays':30,'storage':storage_policy()},headers=headers)
                if method=='DELETE':
                    db.execute('DELETE FROM limits WHERE bucket=?',(sid,))
                    db.execute('DELETE FROM sessions WHERE id=?',(sid,))
                    db.commit()
                    return self.respond(204,headers={'Set-Cookie':'smarttrip_session=; Max-Age=0; HttpOnly; SameSite=Strict; Path=/'+('; Secure' if SECURE else '')})
            if path=='/api/intake' and method=='POST':
                message=payload.get('message','')
                if not isinstance(message,str) or not 1<=len(message.strip())<=2000:
                    raise Problem('Enter a message of 1–2,000 characters.')
                db.commit()
                return self.respond(200,extract_intake(message))
            if path=='/api/trips':
                if method=='GET':
                    rows=db.execute('SELECT data FROM trips WHERE session=? ORDER BY updated DESC',(sid,)).fetchall()
                    return self.respond(200,{'trips':[json.loads(row['data']) for row in rows]})
                if method=='POST':
                    details=validate_details(payload)
                    trip={'id':uuid.uuid4().hex,'details':details,'intakeRevision':1,'confirmedRevision':None,
                          'state':'collecting','itinerary':None,'messages':[],'changes':[],'updatedAt':now()}
                    db.execute('INSERT INTO trips VALUES(?,?,?,?)',(trip['id'],sid,now(),json.dumps(trip)))
                    db.execute('UPDATE sessions SET updated=? WHERE id=?',(now(),sid))
                    db.commit()
                    return self.respond(201,trip)
            parts=path.strip('/').split('/')
            if len(parts) not in [3,4] or parts[:2]!=['api','trips']:
                raise Problem('Endpoint not found.',404,code='NOT_FOUND')
            trip_id=parts[2]
            row=db.execute('SELECT data FROM trips WHERE id=? AND session=?',(trip_id,sid)).fetchone()
            if not row: raise Problem('Trip not found.',404,code='NOT_FOUND')
            trip=json.loads(row['data'])
            action=parts[3] if len(parts)==4 else ''
            if method=='GET' and action=='': return self.respond(200,trip)
            if method=='GET' and action=='export':
                p=trip['itinerary']
                if not p: raise Problem('Generate a plan first.',409,code='NO_ITINERARY')
                fmt=parse_qs(urlparse(self.path).query).get('format',['json'])[0]
                if fmt not in ['json','markdown']: raise Problem('Choose JSON or Markdown.',400)
                return self.respond(200,p if fmt=='json' else markdown(p),
                    'application/json; charset=utf-8' if fmt=='json' else 'text/markdown; charset=utf-8',
                    {'Content-Disposition':f'attachment; filename="smarttrip-{trip_id}.{ "json" if fmt=="json" else "md"}"'})
            if method=='DELETE' and action=='':
                db.execute('DELETE FROM trips WHERE id=? AND session=?',(trip_id,sid))
                db.commit()
                return self.respond(204)
            key=None
            fingerprint=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
            if method=='POST' and action in ['generate','revise']:
                key=self.headers.get('Idempotency-Key','')
                if not 8<=len(key)<=128: raise Problem('Provide an idempotency key of 8–128 characters.',400)
                old=db.execute('SELECT data,fingerprint FROM results WHERE session=? AND trip=? AND scope=? AND key=?',(sid,trip_id,action,key)).fetchone()
                if old:
                    if old['fingerprint']!=fingerprint: raise Problem('Use a new request key for a different request.',409,code='IDEMPOTENCY_CONFLICT')
                    return self.respond(200,json.loads(old['data']))
            if method=='PATCH' and action=='':
                if payload.get('expectedIntakeRevision')!=trip['intakeRevision']:
                    raise Problem('Trip details changed in another tab. Reload and retry.',409,code='REVISION_CONFLICT')
                trip['details']=validate_details(payload.get('details',{}))
                trip['intakeRevision']+=1
                trip['confirmedRevision']=None
                trip['state']='awaiting_confirmation'
            elif method=='POST' and action=='confirm':
                if payload.get('expectedIntakeRevision')!=trip['intakeRevision']:
                    raise Problem('Details have changed. Review the latest summary.',409,code='REVISION_CONFLICT')
                trip['confirmedRevision']=trip['intakeRevision']
                trip['state']='planning'
            elif method=='POST' and action=='generate':
                if trip['confirmedRevision']!=trip['intakeRevision'] or payload.get('expectedIntakeRevision')!=trip['intakeRevision']:
                    raise Problem('Review and confirm your current trip details first.',409,code='CONFIRMATION_REQUIRED')
                current=trip['itinerary']['revision'] if trip['itinerary'] else 0
                if payload.get('expectedRevision')!=current:
                    raise Problem('The plan changed in another tab. Reload and retry.',409,code='REVISION_CONFLICT')
                p=DemoProvider().generate(trip_id,trip['details'])
                p['revision']=current+1
                trip['itinerary']=p
                trip['state']='reviewing'
                trip['changes']=['Generated a fictional demo plan from your confirmed details.']
            elif method=='POST' and action=='revise':
                if not trip['itinerary'] or trip['confirmedRevision']!=trip['intakeRevision']:
                    raise Problem('Confirm and generate the current details before revising.',409,code='CONFIRMATION_REQUIRED')
                if payload.get('expectedRevision')!=trip['itinerary']['revision']:
                    raise Problem('The plan changed in another tab. Reload to get the latest revision.',409,code='REVISION_CONFLICT')
                trip['itinerary'],change=revise(trip['itinerary'],payload)
                trip['changes']=[change]
                if payload.get('request'):
                    trip['messages'] += [{'role':'user','text':payload['request']},{'role':'assistant','text':change}]
                trip['state']='reviewing'
            elif method=='POST' and action=='messages':
                message=payload.get('message','')
                if not isinstance(message,str) or not 1<=len(message.strip())<=2000:
                    raise Problem('Enter a message of 1–2,000 characters.')
                extracted=extract_intake(message)
                fields=dict(extracted['fields'])
                if fields:
                    details=dict(trip['details'])
                    if 'budget' in fields:
                        from planner import CURRENCIES
                        currency=fields.get('currency',details['currency'])
                        fields['budgetMinor']=round(float(fields.pop('budget'))*10**CURRENCIES[currency])
                    details.update(fields)
                    trip['details']=validate_details(details)
                    trip['intakeRevision']+=1
                    trip['confirmedRevision']=None
                    trip['state']='awaiting_confirmation'
                    reply='I updated your trip details from the message. Please review and confirm the new summary before generating a plan.'
                else:
                    reply=chat_reply(message)
                trip['messages'] += [{'role':'user','text':message},{'role':'assistant','text':reply}]
                if not trip['itinerary']: trip['state']='awaiting_confirmation'
            else: raise Problem('Endpoint not found.',404,code='NOT_FOUND')
            trip['messages']=trip['messages'][-60:]
            trip['updatedAt']=now()
            data=json.dumps(trip)
            db.execute('UPDATE trips SET updated=?, data=? WHERE id=? AND session=?',(now(),data,trip_id,sid))
            db.execute('UPDATE sessions SET updated=? WHERE id=?',(now(),sid))
            if key:
                db.execute('INSERT INTO results VALUES(?,?,?,?,?,?)',(sid,trip_id,action,key,fingerprint,data))
            db.commit()
            return self.respond(200,trip)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--cleanup',action='store_true')
    parser.add_argument('--port',type=int,default=int(os.getenv('PORT','8000')))
    args=parser.parse_args()
    init_db()
    if args.cleanup:
        print(f'Removed {cleanup()} expired sessions and their trips.')
        return
    cleanup()
    host=default_host()
    httpd=ThreadingHTTPServer((host,args.port),Handler)
    print(f'SmartTrip AI · demo · http://{host}:{args.port}',flush=True)
    try: httpd.serve_forever()
    except KeyboardInterrupt: pass
    finally: httpd.server_close()

if __name__=='__main__': main()

from flask import Flask, render_template_string, render_template,request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pyotp
import qrcode
import io
import base64
import requests
import os

app = Flask(__name__)
app.secret_key = 'QLL2AYJIS6FKVGWJKVKAKNHWV2ZCI63J' # Clave de sesión
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///agenda.db'
db = SQLAlchemy(app)

# --- CONFIGURACIÓN DE ACCESO DE SEGURIDAD ---
# Contraseña de acceso por defecto
PASSWORD_HASH = "scrypt:32768:8:1$hxlejYJbytJkrb1e$cb4f204ba86359b911f08ef20c65edf365766851cea478499d4efe723e6103ae5552279f91c4efd24ce8fb98e1ff05728c569f5bbe4bef84bf726b2e099e2b8d"
# Clave base32 aleatoria para el 2FA (Se puede generar otra con pyotp.random_base32())
TOTP_SECRET = "6NFLADNC76FMZUYIYK2FX6NA66OIYRBO"

# Configuración del canal de ntfy
NTFY_URL = "https://ntfy.sh/mi_agenda_raspi"

# --- MODELO DE LA BASE DE DATOS ---
class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(100), nullable=False)
    fecha_hora = db.Column(db.String(16), nullable=False) # Formato YYYY-MM-DDTHH:MM
    mensaje = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()

# --- VISTAS DE AUTENTICACIÓN ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        code = request.form['code']
        
        # 1. Validar Contraseña
        if check_password_hash(PASSWORD_HASH, password):
            # 2. Validar Token 2FA (Código de 6 dígitos del móvil)
            totp = pyotp.TOTP(TOTP_SECRET)
            if totp.verify(code):
                session['autenticado'] = True
                return redirect(url_for('index'))
            else:
                flash('Código 2FA incorrecto o caducado.')
        else:
            flash('Contraseña incorrecta.')
            
    # Interfaz básica de Login incrustada
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Login Seguro - Agenda</title>
            <style>
                body { background: #131313; color: #eaeaea; font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .login-card { background: #2b2b2b; padding: 30px; border-radius: 6px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); width: 300px; }
                input { width: 100%; padding: 10px; margin: 10px 0; border-radius: 4px; border: 1px solid #444; background: #131313; color: #fff; box-sizing: border-box; }
                button { width: 100%; padding: 10px; background: #3367d6; color: white; border: none; border-radius: 4px; cursor: pointer; }
                button:hover { background: #4285f4; }
                .error { color: #ffdd57; font-size: 0.9rem; }
            </style>
        </head>
        <body>
            <div class="login-card">
                <h2>🔐 Acceso Protegido</h2>
                {% with messages = get_flashed_messages() %}{% if messages %}<p class="error">{{ messages[0] }}</p>{% endif %}{% endwith %}
                <form method="POST">
                    <input type="password" name="password" placeholder="Contraseña del Servidor" required>
                    <input type="text" name="code" placeholder="Código 2FA (6 dígitos)" autocomplete="off" required>
                    <button type="submit">Verificar Identidad</button>
                </form>
            </div>
        </body>
        </html>
    ''')

# --- PANEL DE CONTROL DE LA AGENDA (PROTEGIDO) ---
@app.route('/')
def index():
    if not session.get('autenticado'):
        return redirect(url_for('login'))
    
    eventos = Evento.query.order_by(Evento.fecha_hora).all()
    
    # Interfaz de gestión
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Panel de Control - Agenda</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            <style>
                body { background: #131313; color: #eaeaea; font-family: sans-serif; padding: 40px 20px; display: flex; flex-direction: column; align-items: center; }
                .container { width: 100%; max-width: 800px; }
                .header-bar { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #2b2b2b; padding-bottom: 10px; margin-bottom: 20px; }
                .card { background: #2b2b2b; padding: 20px; border-radius: 6px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
                input, textarea { width: 100%; padding: 10px; margin: 8px 0; border-radius: 4px; border: 1px solid #444; background: #131313; color: #fff; box-sizing: border-box; }
                .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
                button { padding: 10px 20px; background: #3367d6; color: white; border: none; border-radius: 4px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
                button:hover { background: #4285f4; }
                .btn-danger { background: #d9534f; } .btn-danger:hover { background: #c9302c; }
                .event-item { background: #2b2b2b; padding: 15px; border-radius: 6px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid #3367d6; }
                .logout { color: #a0a0a0; text-decoration: none; } .logout:hover { color: #fff; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header-bar">
                    <h1>📅 Gestión de Notificaciones</h1>
                    <a href="/logout" class="logout"><i class="fas fa-sign-out-alt"></i> Salir</a>
                </div>
                
                <div class="card">
                    <h3><i class="fas fa-plus"></i> Programar Nueva Alerta</h3>
                    <form action="/add" method="POST">
                        <div class="grid">
                            <input type="text" name="titulo" placeholder="Título del evento (Ej: Clase máster)" required>
                            <input type="datetime-local" name="fecha_hora" required>
                        </div>
                        <textarea name="mensaje" placeholder="Mensaje descriptivo que llegará al móvil..." rows="2" required></textarea>
                        <button type="submit"><i class="fas fa-save"></i> Guardar Alerta</button>
                    </form>
                </div>

                <h3><i class="fas fa-bell"></i> Alertas en Base de Datos</h3>
                {% for e in eventos %}
                <div class="event-item">
                    <div>
                        <strong>{{ e.titulo }}</strong> <span style="color: #4285f4; margin-left:10px;">🕒 {{ e.fecha_hora.replace('T', ' ') }}</span>
                        <div style="color: #a0a0a0; font-size: 0.9rem; margin-top: 4px;">{{ e.mensaje }}</div>
                    </div>
                    <a href="/delete/{{ e.id }}" class="btn-danger" style="padding: 8px 12px; border-radius:4px; color:white; text-decoration:none;"><i class="fas fa-trash"></i></a>
                </div>
                {% else %}
                <p style="color: #666;">No hay eventos programados en este momento.</p>
                {% endfor %}
            </div>
        </body>
        </html>
    ''', eventos=eventos)

@app.route('/add', methods=['POST'])
def add_event():
    if not session.get('autenticado'): return redirect(url_for('login'))
    nuevo = Evento(titulo=request.form['titulo'], fecha_hora=request.form['fecha_hora'], mensaje=request.form['mensaje'])
    db.session.add(nuevo)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_event(id):
    if not session.get('autenticado'): return redirect(url_for('login'))
    evento = Evento.query.get_or_create(id)[0] if hasattr(Evento.query, 'get_or_create') else Evento.query.get(id)
    if evento:
        db.session.delete(evento)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('autenticado', None)
    return redirect(url_for('login'))

# --- UTILIDAD: GENERAR CÓDIGO QR PARA EL MÓVIL ---
@app.route('/setup-2fa')
def setup_2fa():
    # Esta ruta te genera el QR para escanear con Google Authenticator / Authy / Bitwarden
    totp = pyotp.TOTP(TOTP_SECRET)
    url_qr = totp.provisioning_uri(name="AdminRaspi", issuer_name="AgendaLocal")
    img = qrcode.make(url_qr)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f'<h2>Escanea este QR con tu app de autenticación móvil:</h2><img src="data:image/png;base64,{img_b64}">'

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)

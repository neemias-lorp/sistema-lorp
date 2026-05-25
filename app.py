from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lorp-universal-chave-segura-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lorp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
DOWNLOAD_FOLDER = 'static/downloads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ============================================================
# MODELOS DO BANCO DE DADOS
# ============================================================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean, default=True)

class Pergunta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(300), nullable=False)
    pergunta = db.Column(db.Text, nullable=False)
    resposta = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(100), default='Geral')
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ordem = db.Column(db.Integer, default=0)
    destaque = db.Column(db.Boolean, default=False)
    imagem = db.Column(db.String(200))
    views = db.Column(db.Integer, default=0)

class Descoberta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(300), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    protocolo = db.Column(db.String(100))
    previsibilidade = db.Column(db.String(50))
    categoria = db.Column(db.String(100), default='Paleografia')
    data_registro = db.Column(db.DateTime, default=datetime.utcnow)
    icone = db.Column(db.String(50), default='🏆')

class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    lida = db.Column(db.Boolean, default=False)

class Visita(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, default=date.today)
    visitas = db.Column(db.Integer, default=0)

class Imagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    titulo = db.Column(db.String(200))
    descricao = db.Column(db.Text)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    categoria = db.Column(db.String(100), default='geral')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================
# CONTADOR DE VISITAS
# ============================================================

@app.before_request
def contar_visita():
    if request.endpoint and 'static' not in request.endpoint and 'api' not in request.endpoint:
        try:
            hoje = date.today()
            visita = Visita.query.filter_by(data=hoje).first()
            if visita:
                visita.visitas += 1
            else:
                visita = Visita(data=hoje, visitas=1)
                db.session.add(visita)
            db.session.commit()
        except:
            pass

def get_visitas():
    try:
        hoje = date.today()
        visita_hoje = Visita.query.filter_by(data=hoje).first()
        total = db.session.query(db.func.sum(Visita.visitas)).scalar() or 0
        return {'hoje': visita_hoje.visitas if visita_hoje else 0, 'total': total}
    except:
        return {'hoje': 0, 'total': 0}

# ============================================================
# AUTÔMATO AAA B
# ============================================================

class AutomatoAAAB:
    def __init__(self):
        self.estado_atual = "A1"
        self.historico = []
    
    def transicionar(self, simbolo: str):
        origem = self.estado_atual
        if self.estado_atual == "A1" and simbolo.upper() == "A":
            self.estado_atual = "A2"
        elif self.estado_atual == "A2" and simbolo.upper() == "A":
            self.estado_atual = "A3"
        elif self.estado_atual == "A3" and simbolo.upper() == "B":
            self.estado_atual = "B"
        elif self.estado_atual == "B" and simbolo.upper() == "A":
            self.estado_atual = "A1"
        self.historico.append({"origem": origem, "destino": self.estado_atual, "simbolo": simbolo})
        return self.estado_atual
    
    def get_previsibilidade(self):
        if not self.historico:
            return 0.0
        validas = sum(1 for t in self.historico if t["origem"] != t["destino"])
        return (validas / len(self.historico)) * 100

# ============================================================
# ROTAS PÚBLICAS
# ============================================================

@app.route('/')
def index():
    perguntas = Pergunta.query.filter_by(destaque=True).order_by(Pergunta.ordem).limit(6).all()
    descobertas = Descoberta.query.order_by(Descoberta.data_registro.desc()).limit(6).all()
    imagens = Imagem.query.order_by(Imagem.data_upload.desc()).limit(12).all()
    visitas = get_visitas()
    return render_template('index.html', perguntas=perguntas, descobertas=descobertas, imagens=imagens, visitas=visitas)

@app.route('/perguntas')
def todas_perguntas():
    page = request.args.get('page', 1, type=int)
    categoria = request.args.get('categoria', '')
    search = request.args.get('search', '')
    
    query = Pergunta.query
    if categoria:
        query = query.filter_by(categoria=categoria)
    if search:
        query = query.filter(
            db.or_(
                Pergunta.titulo.contains(search),
                Pergunta.pergunta.contains(search),
                Pergunta.resposta.contains(search)
            )
        )
    
    perguntas = query.order_by(Pergunta.ordem, Pergunta.data_criacao.desc()).paginate(page=page, per_page=20)
    categorias = db.session.query(Pergunta.categoria, db.func.count(Pergunta.id)).group_by(Pergunta.categoria).all()
    visitas = get_visitas()
    
    return render_template('perguntas.html', perguntas=perguntas, categorias=categorias, search=search, categoria_atual=categoria, visitas=visitas)

@app.route('/pergunta/<int:id>')
def ver_pergunta(id):
    pergunta = Pergunta.query.get_or_404(id)
    pergunta.views += 1
    db.session.commit()
    visitas = get_visitas()
    return render_template('ver_pergunta.html', pergunta=pergunta, visitas=visitas)

@app.route('/galeria')
def galeria():
    imagens = Imagem.query.order_by(Imagem.data_upload.desc()).all()
    visitas = get_visitas()
    return render_template('galeria.html', imagens=imagens, visitas=visitas)

@app.route('/downloads')
def downloads():
    visitas = get_visitas()
    return render_template('downloads.html', visitas=visitas)

@app.route('/enviar-mensagem', methods=['POST'])
def enviar_mensagem():
    msg = Mensagem(
        nome=request.form['nome'],
        email=request.form['email'],
        mensagem=request.form['mensagem']
    )
    db.session.add(msg)
    db.session.commit()
    flash('✅ Mensagem enviada com sucesso!', 'success')
    return redirect(url_for('index'))

@app.route('/api/automato', methods=['POST'])
def api_automato():
    data = request.get_json()
    sequencia = data.get('sequencia', [])
    automato = AutomatoAAAB()
    for s in sequencia:
        automato.transicionar(s)
    return jsonify({
        'estado_final': automato.estado_atual,
        'previsibilidade': automato.get_previsibilidade(),
        'historico': automato.historico
    })

# ============================================================
# ROTAS ADMINISTRATIVAS
# ============================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return redirect(url_for('admin'))
        flash('Usuário ou senha inválidos')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    perguntas = Pergunta.query.order_by(Pergunta.ordem).all()
    descobertas = Descoberta.query.order_by(Descoberta.data_registro.desc()).all()
    mensagens = Mensagem.query.order_by(Mensagem.data.desc()).limit(20).all()
    imagens = Imagem.query.order_by(Imagem.data_upload.desc()).all()
    visitas = get_visitas()
    return render_template('admin.html', perguntas=perguntas, descobertas=descobertas, mensagens=mensagens, imagens=imagens, visitas=visitas)

@app.route('/admin/pergunta/nova', methods=['GET', 'POST'])
@login_required
def nova_pergunta():
    if request.method == 'POST':
        pergunta = Pergunta(
            titulo=request.form['titulo'],
            pergunta=request.form['pergunta'],
            resposta=request.form['resposta'],
            categoria=request.form['categoria'],
            ordem=int(request.form.get('ordem', 0)),
            destaque='destaque' in request.form
        )
        db.session.add(pergunta)
        db.session.commit()
        flash('✅ Pergunta criada com sucesso!', 'success')
        return redirect(url_for('admin'))
    return render_template('new.html')

@app.route('/admin/pergunta/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_pergunta(id):
    pergunta = Pergunta.query.get_or_404(id)
    if request.method == 'POST':
        pergunta.titulo = request.form['titulo']
        pergunta.pergunta = request.form['pergunta']
        pergunta.resposta = request.form['resposta']
        pergunta.categoria = request.form['categoria']
        pergunta.ordem = int(request.form.get('ordem', 0))
        pergunta.destaque = 'destaque' in request.form
        db.session.commit()
        flash('✅ Pergunta atualizada!', 'success')
        return redirect(url_for('admin'))
    return render_template('edit.html', pergunta=pergunta)

@app.route('/admin/pergunta/excluir/<int:id>')
@login_required
def excluir_pergunta(id):
    pergunta = Pergunta.query.get_or_404(id)
    db.session.delete(pergunta)
    db.session.commit()
    flash('🗑️ Pergunta excluída!', 'warning')
    return redirect(url_for('admin'))

@app.route('/admin/descoberta/nova', methods=['POST'])
@login_required
def nova_descoberta():
    descoberta = Descoberta(
        titulo=request.form['titulo'],
        descricao=request.form['descricao'],
        protocolo=request.form.get('protocolo', ''),
        previsibilidade=request.form.get('previsibilidade', ''),
        categoria=request.form['categoria']
    )
    db.session.add(descoberta)
    db.session.commit()
    flash('✅ Descoberta adicionada!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/descoberta/excluir/<int:id>')
@login_required
def excluir_descoberta(id):
    descoberta = Descoberta.query.get_or_404(id)
    db.session.delete(descoberta)
    db.session.commit()
    flash('🗑️ Descoberta excluída!', 'warning')
    return redirect(url_for('admin'))

@app.route('/admin/mensagem/marcar-lida/<int:id>')
@login_required
def marcar_lida(id):
    msg = Mensagem.query.get_or_404(id)
    msg.lida = True
    db.session.commit()
    flash('✅ Mensagem marcada como lida', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/upload', methods=['POST'])
@login_required
def upload_imagem():
    if 'file' not in request.files:
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('admin'))
    
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{name}_{timestamp}{ext}"
        
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        img = Imagem(
            filename=filename,
            titulo=request.form.get('titulo', filename),
            descricao=request.form.get('descricao', ''),
            categoria=request.form.get('categoria', 'geral')
        )
        db.session.add(img)
        db.session.commit()
        flash(f'✅ Imagem {filename} enviada com sucesso!', 'success')
    else:
        flash('❌ Formato não permitido', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/imagem/excluir/<int:id>')
@login_required
def excluir_imagem(id):
    img = Imagem.query.get_or_404(id)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    db.session.delete(img)
    db.session.commit()
    flash('🗑️ Imagem excluída!', 'warning')
    return redirect(url_for('admin'))

# ============================================================
# INICIALIZAÇÃO
# ============================================================

def init_db():
    with app.app_context():
        db.create_all()
        
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                email='contato@lorp.org'
            )
            db.session.add(admin)
        
        db.session.commit()
        print("✅ Banco inicializado! Usuário: admin / senha: admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

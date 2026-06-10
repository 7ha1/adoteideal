import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
from models import db, Ong, Pet, Interesse
from matching import get_pets_recomendados, formatar_recomendacao
import cloudinary
import cloudinary.uploader
import cloudinary.api

basedir = os.path.abspath(os.path.dirname(__file__))
instance_path = os.path.join(basedir, 'instance')
os.makedirs(instance_path, exist_ok=True)

app = Flask(__name__, instance_path=instance_path)

# Configurações de Sessão
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-mudar-em-producao')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração do Cloudinary
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
    api_key=os.environ.get('CLOUDINARY_API_KEY'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET')
)

# Configuração do Banco de Dados
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
    elif DATABASE_URL.startswith('postgresql://'):
        DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    print("✅ Usando PostgreSQL no Render")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'pets.db')
    print("✅ Usando SQLite (local)")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)

with app.app_context():
    db.create_all()
    print("✅ Banco de dados inicializado")

# --- Função auxiliar para fazer upload seguro ---
def upload_imagem_sem_crop(file):
    """
    Faz upload para o Cloudinary sem aplicar crop.
    Aplica apenas um limite de largura máxima de 800px e mantém proporção.
    """
    try:
        upload_result = cloudinary.uploader.upload(
            file,
            folder="adoteideal_pets",
            transformation=[
                {"width": 800, "crop": "limit"}
            ]
        )
        return upload_result['secure_url']
    except Exception as e:
        print(f"Erro no upload: {e}")
        return None

# --- ROTAS PRINCIPAIS ---
@app.route('/')
def index():
    pets = Pet.query.order_by(Pet.id.desc()).limit(6).all()
    return render_template('index.html', pets=pets)

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/questionario', methods=['GET', 'POST'])
def questionario():
    if request.method == 'POST':
        session['prefs'] = {
            'especie': request.form.get('especie'),
            'porte': request.form.get('porte'),
            'energia': request.form.get('energia'),
            'moradia': request.form.get('moradia'),
            'tempo_ausente': request.form.get('tempo_ausente'),
            'criancas': request.form.get('criancas'),
            'outros_pets': request.form.get('outros_pets'),
            'experiencia': request.form.get('experiencia'),
            'tolerancia': request.form.get('tolerancia'),
            'idade_preferida': request.form.get('idade_preferida'),
            'sexo': request.form.get('sexo'),
            'castrado': request.form.get('castrado')
        }
        return redirect(url_for('resultados'))
    return render_template('questionario.html')

@app.route('/resultados')
def resultados():
    prefs = session.get('prefs')
    if not prefs:
        return redirect(url_for('questionario'))
    todos_pets = Pet.query.all()
    recomendados = get_pets_recomendados(prefs, todos_pets)
    resultados_formatados = [formatar_recomendacao(r) for r in recomendados]
    return render_template('resultados.html', resultados=resultados_formatados, prefs=prefs)

@app.route('/pet/<int:pet_id>')
def pet_detalhe(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    return render_template('pet_detalhe.html', pet=pet)

@app.route('/interesse/<int:pet_id>', methods=['GET', 'POST'])
def interesse(pet_id):
    pet = Pet.query.get_or_404(pet_id)
    if request.method == 'POST':
        interesse = Interesse(
            pet_id=pet_id,
            nome_adotante=request.form.get('nome'),
            telefone=request.form.get('telefone'),
            mensagem=request.form.get('mensagem', '')
        )
        db.session.add(interesse)
        db.session.commit()
        flash('Interesse registrado! A ONG entrará em contato.', 'success')
        return redirect(url_for('obrigado'))
    return render_template('interesse_form.html', pet=pet)

@app.route('/obrigado')
def obrigado():
    return render_template('obrigado.html')

# --- Página com todos os pets  ---
@app.route('/pets')
def todos_pets():
    todos = Pet.query.order_by(Pet.id.desc()).all()
    return render_template('todos_pets.html', pets=todos)

# --- ROTAS DA ONG ---
@app.route('/ong/cadastrar', methods=['GET', 'POST'])
def ong_cadastrar():
    if request.method == 'POST':
        username = request.form.get('username')
        senha = request.form.get('senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if senha != confirmar_senha:
            flash('As senhas não coincidem.', 'error')
            return redirect(url_for('ong_cadastrar'))
        
        if Ong.query.filter_by(username=username).first():
            flash('Usuário já existe.', 'error')
            return redirect(url_for('ong_cadastrar'))
        
        ong = Ong(
            username=username,
            nome_ong=request.form.get('nome_ong'),
            email=request.form.get('email'),
            telefone=request.form.get('telefone'),
            whatsapp=request.form.get('whatsapp'),
            cidade=request.form.get('cidade'),
            endereco=request.form.get('endereco')
        )
        ong.set_password(senha)
        db.session.add(ong)
        db.session.commit()
        flash('Cadastro realizado! Faça login.', 'success')
        return redirect(url_for('ong_login'))
    return render_template('ong_cadastrar.html')

@app.route('/ong/login', methods=['GET', 'POST'])
def ong_login():
    if request.method == 'POST':
        ong = Ong.query.filter_by(username=request.form.get('username')).first()
        if ong and ong.check_password(request.form.get('senha')):
            session['ong_id'] = ong.id
            session['ong_nome'] = ong.nome_ong
            session.permanent = True
            flash(f'Bem-vindo(a), {ong.nome_ong}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Usuário ou senha inválidos.', 'error')
    return render_template('ong_login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('ong_id'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('ong_login'))
    ong = Ong.query.get(session['ong_id'])
    pets = Pet.query.filter_by(ong_id=ong.id).all()
    interesses = Interesse.query.join(Pet).filter(Pet.ong_id == ong.id).all()
    return render_template('dashboard.html', pets=pets, interesses=interesses, ong=ong)

# --- CADASTRO DE PET ---
@app.route('/cadastrar_pet', methods=['GET', 'POST'])
def cadastrar_pet():
    if not session.get('ong_id'):
        return redirect(url_for('ong_login'))
    if request.method == 'POST':
        idade_valor = int(request.form.get('idade_valor', 0))
        idade_unidade = request.form.get('idade_unidade', 'meses')
        idade_meses = idade_valor * 12 if idade_unidade == 'anos' else idade_valor

        foto_url = 'https://placehold.co/800x400/e8e2d4/8a9a8a?text=AdoteIdeal'

        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename and allowed_file(file.filename):
                uploaded_url = upload_imagem_sem_crop(file)
                if uploaded_url:
                    foto_url = uploaded_url
                else:
                    flash('Erro no upload da imagem. Usando imagem padrão.', 'error')

        pet = Pet(
            nome=request.form.get('nome'),
            especie=request.form.get('especie'),
            sexo=request.form.get('sexo'),
            porte=request.form.get('porte'),
            idade_meses=idade_meses,
            energia=request.form.get('energia', 'media'),
            aceita_criancas='aceita_criancas' in request.form,
            aceita_gatos='aceita_gatos' in request.form,
            aceita_caes='aceita_caes' in request.form,
            vacinado='vacinado' in request.form,
            castrado='castrado' in request.form,
            descricao=request.form.get('descricao', ''),
            foto_url=foto_url,
            ong_id=session['ong_id'],
            independencia=request.form.get('independencia', 'media'),
            vocalizacao=request.form.get('vocalizacao', 'media'),
            aceita_desconhecidos='aceita_desconhecidos' in request.form,
            necessidades_especiais='necessidades_especiais' in request.form,
            nivel_atividade=request.form.get('nivel_atividade', 'media')
        )
        db.session.add(pet)
        db.session.commit()
        flash(f'{pet.nome} cadastrado!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('cadastrar_pet.html')

# --- EDIÇÃO DE PET ---
@app.route('/editar_pet/<int:pet_id>', methods=['GET', 'POST'])
def editar_pet(pet_id):
    if not session.get('ong_id'):
        return redirect(url_for('ong_login'))
    pet = Pet.query.get_or_404(pet_id)
    if pet.ong_id != session['ong_id']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        pet.nome = request.form.get('nome')
        pet.especie = request.form.get('especie')
        pet.sexo = request.form.get('sexo')
        pet.porte = request.form.get('porte')
        idade_valor = int(request.form.get('idade_valor', 0))
        idade_unidade = request.form.get('idade_unidade', 'meses')
        pet.idade_meses = idade_valor * 12 if idade_unidade == 'anos' else idade_valor
        pet.energia = request.form.get('energia', 'media')
        pet.aceita_criancas = 'aceita_criancas' in request.form
        pet.aceita_gatos = 'aceita_gatos' in request.form
        pet.aceita_caes = 'aceita_caes' in request.form
        pet.vacinado = 'vacinado' in request.form
        pet.castrado = 'castrado' in request.form
        pet.descricao = request.form.get('descricao', '')
        
        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename and allowed_file(file.filename):
                uploaded_url = upload_imagem_sem_crop(file)
                if uploaded_url:
                    pet.foto_url = uploaded_url
                else:
                    flash('Erro ao atualizar foto.', 'error')
        
        pet.independencia = request.form.get('independencia', 'media')
        pet.vocalizacao = request.form.get('vocalizacao', 'media')
        pet.aceita_desconhecidos = 'aceita_desconhecidos' in request.form
        pet.necessidades_especiais = 'necessidades_especiais' in request.form
        pet.nivel_atividade = request.form.get('nivel_atividade', 'media')
        db.session.commit()
        flash('Pet atualizado!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('editar_pet.html', pet=pet)

@app.route('/excluir_pet/<int:pet_id>')
def excluir_pet(pet_id):
    if not session.get('ong_id'):
        return redirect(url_for('ong_login'))
    pet = Pet.query.get_or_404(pet_id)
    if pet.ong_id != session['ong_id']:
        flash('Acesso negado.', 'error')
        return redirect(url_for('dashboard'))
    db.session.delete(pet)
    db.session.commit()
    flash('Pet removido.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/ong/perfil', methods=['GET', 'POST'])
def ong_perfil():
    if not session.get('ong_id'):
        return redirect(url_for('ong_login'))
    ong = Ong.query.get(session['ong_id'])
    if request.method == 'POST':
        ong.nome_ong = request.form.get('nome_ong')
        ong.email = request.form.get('email')
        ong.telefone = request.form.get('telefone')
        ong.whatsapp = request.form.get('whatsapp')
        ong.cidade = request.form.get('cidade')
        ong.endereco = request.form.get('endereco')
        if request.form.get('nova_senha'):
            ong.set_password(request.form.get('nova_senha'))
        db.session.commit()
        session['ong_nome'] = ong.nome_ong
        flash('Perfil atualizado!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('ong_perfil.html', ong=ong)

@app.route('/ong/excluir', methods=['POST'])
def ong_excluir():
    if not session.get('ong_id'):
        flash('Acesso negado.', 'error')
        return redirect(url_for('ong_login'))
    ong = Ong.query.get(session['ong_id'])
    if not ong:
        flash('ONG não encontrada.', 'error')
        return redirect(url_for('logout'))
    confirmar = request.form.get('confirmar')
    if confirmar != 'SIM':
        flash('Para excluir, digite SIM no campo de confirmação.', 'error')
        return redirect(url_for('ong_perfil'))
    db.session.delete(ong)
    db.session.commit()
    session.clear()
    flash('Sua conta foi excluída permanentemente.', 'info')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout efetuado.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
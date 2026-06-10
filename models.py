from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Ong(db.Model):
    __tablename__ = 'ongs'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    nome_ong = db.Column(db.String(200), nullable=False, default='ONG Parceira')
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))
    cidade = db.Column(db.String(100))
    endereco = db.Column(db.String(200))
    
    pets = db.relationship('Pet', backref='ong', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Pet(db.Model):
    __tablename__ = 'pets'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    especie = db.Column(db.String(50), nullable=False)
    sexo = db.Column(db.String(20))
    porte = db.Column(db.String(20), nullable=False)
    idade_meses = db.Column(db.Integer, nullable=False)
    energia = db.Column(db.String(20), default='media')
    aceita_criancas = db.Column(db.Boolean, default=True)
    aceita_gatos = db.Column(db.Boolean, default=True)
    aceita_caes = db.Column(db.Boolean, default=True)
    vacinado = db.Column(db.Boolean, default=False)
    castrado = db.Column(db.Boolean, default=False)
    descricao = db.Column(db.Text, default='')
    foto_url = db.Column(db.String(500), default='/static/uploads/default.jpg')
    ong_id = db.Column(db.Integer, db.ForeignKey('ongs.id', ondelete='CASCADE'))
    
    independencia = db.Column(db.String(20), default='media')
    vocalizacao = db.Column(db.String(20), default='media')
    aceita_desconhecidos = db.Column(db.Boolean, default=True)
    necessidades_especiais = db.Column(db.Boolean, default=False)
    nivel_atividade = db.Column(db.String(20), default='media')
    
    interesses = db.relationship('Interesse', backref='pet', lazy=True, cascade="all, delete-orphan")


class Interesse(db.Model):
    __tablename__ = 'interesses'
    
    id = db.Column(db.Integer, primary_key=True)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id', ondelete='CASCADE'))
    nome_adotante = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    mensagem = db.Column(db.Text)
    data_registro = db.Column(db.DateTime, default=db.func.current_timestamp())
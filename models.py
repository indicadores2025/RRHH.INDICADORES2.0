# models.py

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Unidad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(128), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='usuario')
    activo = db.Column(db.Boolean, default=True)
    unidad_id = db.Column(db.Integer, db.ForeignKey('unidad.id'), nullable=True)

class Pregunta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    texto = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'texto', 'numerico'
    nivel = db.Column(db.Integer, nullable=False, default=1)
    padre_id = db.Column(db.Integer, db.ForeignKey('pregunta.id'), nullable=True)
    unidad_id = db.Column(db.Integer, db.ForeignKey('unidad.id'), nullable=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

class Periodo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mes = db.Column(db.Integer, nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    abierto = db.Column(db.Boolean, default=True)
    fecha_apertura = db.Column(db.DateTime)
    fecha_cierre = db.Column(db.DateTime)

class Respuesta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    pregunta_id = db.Column(db.Integer, db.ForeignKey('pregunta.id'))
    unidad_id = db.Column(db.Integer, db.ForeignKey('unidad.id'))
    periodo_id = db.Column(db.Integer, db.ForeignKey('periodo.id'))
    valor = db.Column(db.String(255), nullable=False)   # <-- acepta texto o número
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

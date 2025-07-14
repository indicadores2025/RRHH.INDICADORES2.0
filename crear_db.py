from flask import Flask
from models import db, Usuario
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sistema.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Elimina la base anterior si existe (opcional, para pruebas)
if os.path.exists("sistema.db"):
    os.remove("sistema.db")

with app.app_context():
    db.create_all()

    # Crea solo el usuario administrador
    admin = Usuario(usuario="admin", password="Admin2025", rol="admin", activo=True)
    db.session.add(admin)
    db.session.commit()

print("✅ Base de datos creada solo con usuario admin (Admin2025).")

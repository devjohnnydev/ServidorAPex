"""
Script para criar usuarios de teste.
Execute uma unica vez: .venv\Scripts\python seed_usuarios.py
"""
import os

os.environ.setdefault("SECRET_KEY", "9397713362883cd7b43d2be212b64a7d663b285ac2e70825b8afab8191bcf52b")
os.environ.setdefault("DATABASE_URL", "sqlite:///local.db")
os.environ.setdefault("UPLOAD_FOLDER", "./uploads")

from app import create_app, db
from app.models import User

app = create_app()

USUARIOS = [
    {"username": "admin",       "nome": "Administrador",    "password": "Admin@123",   "is_admin": True},
    {"username": "funcionario", "nome": "João Funcionário", "password": "Func@2024",   "is_admin": False},
]

with app.app_context():
    db.create_all()
    for dados in USUARIOS:
        existing = User.query.filter_by(username=dados["username"]).first()
        if existing:
            existing.set_password(dados["password"])
            existing.is_admin = dados["is_admin"]
            existing.ativo = True
            print(f"[ATUALIZADO] {dados['username']}")
        else:
            user = User(
                username=dados["username"],
                nome=dados["nome"],
                is_admin=dados["is_admin"],
            )
            user.set_password(dados["password"])
            db.session.add(user)
            print(f"[CRIADO] {dados['username']}")
    db.session.commit()
    print("\nUsuarios prontos para teste:")
    for u in USUARIOS:
        tipo = "ADMIN" if u["is_admin"] else "USUARIO"
        print(f"  [{tipo}] Login: {u['username']}  Senha: {u['password']}")

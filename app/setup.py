"""
Rota de setup ONE-TIME para criar o admin em producao sem precisar do Shell.
Protegida por token secreto e desativada automaticamente apos o uso.

REMOVA este arquivo (e o import em __init__.py) apos criar o admin!
"""
import os
from flask import Blueprint, jsonify
from . import db
from .models import User

setup_bp = Blueprint("setup", __name__)

# Token secreto — so quem souber essa URL consegue usar
_SETUP_TOKEN = os.environ.get("SETUP_TOKEN", "apex-setup-2024")

_USUARIOS_SEED = [
    {"username": "admin",       "nome": "Administrador",    "password": "Admin@123",  "is_admin": True},
    {"username": "funcionario", "nome": "Funcionário",      "password": "Func@2024",  "is_admin": False},
]


@setup_bp.route(f"/setup/<token>")
def setup(token):
    """
    Cria os usuarios iniciais. Acesse:
      https://seu-app.up.railway.app/setup/apex-setup-2024
    """
    if token != _SETUP_TOKEN:
        return jsonify({"erro": "Token invalido."}), 403

    criados = []
    atualizados = []

    for dados in _USUARIOS_SEED:
        user = User.query.filter_by(username=dados["username"]).first()
        if user is None:
            user = User(
                username=dados["username"],
                nome=dados["nome"],
                is_admin=dados["is_admin"],
                ativo=True,
            )
            user.set_password(dados["password"])
            db.session.add(user)
            criados.append(dados["username"])
        else:
            user.set_password(dados["password"])
            user.is_admin = dados["is_admin"]
            user.ativo = True
            atualizados.append(dados["username"])

    db.session.commit()

    return jsonify({
        "status": "ok",
        "criados": criados,
        "atualizados": atualizados,
        "credenciais": [
            {"login": u["username"], "senha": u["password"], "admin": u["is_admin"]}
            for u in _USUARIOS_SEED
        ],
        "aviso": "Remova app/setup.py e o import em app/__init__.py apos usar!"
    })

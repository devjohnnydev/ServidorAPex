import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para continuar."
    login_manager.login_message_category = "warning"
    csrf.init_app(app)

    from . import models  # noqa: F401

    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

    from .auth import auth_bp
    from .notas import notas_bp
    from .setup import setup_bp  # TEMPORARIO — remover apos criar o admin

    app.register_blueprint(auth_bp)
    app.register_blueprint(notas_bp)
    app.register_blueprint(setup_bp)  # TEMPORARIO

    with app.app_context():
        db.create_all()
        _migrar_colunas(db)
        _inicializar_categorias(app, db)

    register_cli(app)

    @app.context_processor
    def inject_globals():
        from .models import Categoria
        todas_categorias = app.config["CATEGORIAS"]
        try:
            cats_db = [c.nome for c in Categoria.query.order_by(Categoria.nome).all()]
            todas_categorias = list(dict.fromkeys(app.config["CATEGORIAS"] + cats_db))
        except Exception:
            db.session.rollback()
        return {
            "categorias": todas_categorias,
            "tipos_documento": app.config["TIPOS_DOCUMENTO"],
            "status_financeiro": app.config["STATUS_FINANCEIRO"],
        }

    return app



def _inicializar_categorias(app, db):
    """Insere as categorias padrao no banco se a tabela estiver vazia."""
    from .models import Categoria
    try:
        if Categoria.query.count() == 0:
            for cat_nome in app.config["CATEGORIAS"]:
                db.session.add(Categoria(nome=cat_nome))
            db.session.commit()
    except Exception:
        db.session.rollback()




def _migrar_colunas(db):
    """Adiciona colunas novas a tabelas ja existentes (safe migration)."""
    from sqlalchemy import text, inspect
    inspector = inspect(db.engine)
    
    colunas_nota = []
    try:
        colunas_nota = [c["name"] for c in inspector.get_columns("nota")]
    except Exception:
        pass

    novas_colunas_nota = [
        ("tipo_documento", "ALTER TABLE nota ADD COLUMN tipo_documento VARCHAR(40) DEFAULT 'Outro'"),
        ("data_vencimento", "ALTER TABLE nota ADD COLUMN data_vencimento DATE"),
        ("data_pagamento", "ALTER TABLE nota ADD COLUMN data_pagamento DATE"),
        ("comprovante_nome", "ALTER TABLE nota ADD COLUMN comprovante_nome VARCHAR(255)"),
        ("comprovante_nome_original", "ALTER TABLE nota ADD COLUMN comprovante_nome_original VARCHAR(255)"),
        ("status", "ALTER TABLE nota ADD COLUMN status VARCHAR(20) DEFAULT 'Pendente'"),
        ("valor_pago", "ALTER TABLE nota ADD COLUMN valor_pago NUMERIC(12,2) DEFAULT 0"),
    ]

    for col_nome, sql_cmd in novas_colunas_nota:
        if col_nome not in colunas_nota:
            try:
                db.session.execute(text(sql_cmd))
                db.session.commit()
            except Exception:
                db.session.rollback()

    try:
        colunas_user = [c["name"] for c in inspector.get_columns("user")]
        if "email" not in colunas_user:
            db.session.execute(text("ALTER TABLE \"user\" ADD COLUMN email VARCHAR(120)"))
            db.session.commit()
    except Exception:
        db.session.rollback()




def register_cli(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Cria as tabelas do banco de dados."""
        with app.app_context():
            db.create_all()
        click.echo("Banco de dados inicializado.")

    @app.cli.command("criar-admin")
    @click.option("--username", prompt=True)
    @click.option("--nome", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def criar_admin(username, nome, password):
        """Cria (ou promove) um usuario administrador."""
        from .models import User

        with app.app_context():
            user = User.query.filter_by(username=username).first()
            if user is None:
                user = User(username=username, nome=nome, is_admin=True)
                user.set_password(password)
                db.session.add(user)
            else:
                user.nome = nome
                user.is_admin = True
                user.set_password(password)
            db.session.commit()
        click.echo(f"Administrador '{username}' pronto.")

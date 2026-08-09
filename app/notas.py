import os
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    send_from_directory, current_app, abort
)
from flask_login import login_required, current_user
from sqlalchemy import func

from . import db
from .models import Nota

notas_bp = Blueprint("notas", __name__)


def arquivo_permitido(nome_arquivo):
    ext = nome_arquivo.rsplit(".", 1)[-1].lower() if "." in nome_arquivo else ""
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def salvar_arquivo(arquivo):
    ext = arquivo.filename.rsplit(".", 1)[-1].lower()
    nome_salvo = f"{uuid.uuid4().hex}.{ext}"
    caminho = os.path.join(current_app.config["UPLOAD_FOLDER"], nome_salvo)
    arquivo.save(caminho)
    return nome_salvo


def parse_data(valor_str, padrao=None):
    try:
        return datetime.strptime(valor_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return padrao


def parse_valor(valor_str):
    try:
        valor_str = (valor_str or "0").replace(".", "").replace(",", ".") \
            if "," in (valor_str or "") else (valor_str or "0")
        return Decimal(valor_str)
    except InvalidOperation:
        return Decimal("0")


@notas_bp.route("/")
@login_required
def dashboard():
    query = Nota.query

    data_inicio = request.args.get("data_inicio", "")
    data_fim = request.args.get("data_fim", "")
    tipo = request.args.get("tipo", "")
    categoria = request.args.get("categoria", "")
    tipo_documento = request.args.get("tipo_documento", "")
    cliente = request.args.get("cliente", "").strip()
    busca = request.args.get("busca", "").strip()

    if data_inicio:
        d = parse_data(data_inicio)
        if d:
            query = query.filter(Nota.data_emissao >= d)
    if data_fim:
        d = parse_data(data_fim)
        if d:
            query = query.filter(Nota.data_emissao <= d)
    if tipo in ("entrada", "saida"):
        query = query.filter(Nota.tipo == tipo)
    if categoria:
        query = query.filter(Nota.categoria == categoria)
    if tipo_documento:
        query = query.filter(Nota.tipo_documento == tipo_documento)
    if cliente:
        query = query.filter(Nota.cliente_fornecedor.ilike(f"%{cliente}%"))
    if busca:
        like = f"%{busca}%"
        query = query.filter(
            db.or_(
                Nota.cliente_fornecedor.ilike(like),
                Nota.numero_nota.ilike(like),
                Nota.descricao.ilike(like),
            )
        )

    notas = query.order_by(Nota.data_emissao.desc(), Nota.id.desc()).all()

    total_entradas = sum((n.valor for n in notas if n.tipo == "entrada"), Decimal("0"))
    total_saidas = sum((n.valor for n in notas if n.tipo == "saida"), Decimal("0"))

    # Lista de clientes/fornecedores distintos para o dropdown
    clientes = [
        r[0] for r in
        db.session.query(Nota.cliente_fornecedor)
        .filter(Nota.cliente_fornecedor.isnot(None))
        .filter(Nota.cliente_fornecedor != "")
        .distinct()
        .order_by(Nota.cliente_fornecedor)
        .all()
    ]

    return render_template(
        "dashboard.html",
        notas=notas,
        total_entradas=total_entradas,
        total_saidas=total_saidas,
        saldo=total_entradas - total_saidas,
        filtros=request.args,
        clientes=clientes,
    )


@notas_bp.route("/notas/nova", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        arquivo = request.files.get("arquivo")

        if not arquivo or arquivo.filename == "":
            flash("Selecione um arquivo (PDF ou foto da nota).", "danger")
            return redirect(url_for("notas.upload"))

        if not arquivo_permitido(arquivo.filename):
            flash("Formato não permitido. Envie PDF, JPG, PNG ou WEBP.", "danger")
            return redirect(url_for("notas.upload"))

        data_emissao = parse_data(request.form.get("data_emissao"), datetime.utcnow().date())

        nota = Nota(
            numero_nota=request.form.get("numero_nota", "").strip(),
            tipo=request.form.get("tipo", "entrada"),
            tipo_documento=request.form.get("tipo_documento", "Outro"),
            categoria=request.form.get("categoria", "").strip(),
            cliente_fornecedor=request.form.get("cliente_fornecedor", "").strip(),
            valor=parse_valor(request.form.get("valor")),
            data_emissao=data_emissao,
            descricao=request.form.get("descricao", "").strip(),
            arquivo_nome_original=arquivo.filename,
            enviado_por_id=current_user.id,
        )
        nota.arquivo_nome = salvar_arquivo(arquivo)

        db.session.add(nota)
        db.session.commit()
        flash("Nota enviada com sucesso.", "success")
        return redirect(url_for("notas.dashboard"))

    return render_template("upload.html", hoje=datetime.utcnow().date().isoformat())


@notas_bp.route("/notas/<int:nota_id>/editar", methods=["GET", "POST"])
@login_required
def editar(nota_id):
    nota = Nota.query.get_or_404(nota_id)
    if not nota.pode_editar(current_user):
        abort(403)

    if request.method == "POST":
        nota.numero_nota = request.form.get("numero_nota", "").strip()
        nota.tipo = request.form.get("tipo", "entrada")
        nota.tipo_documento = request.form.get("tipo_documento", nota.tipo_documento or "Outro")
        nota.categoria = request.form.get("categoria", "").strip()
        nota.cliente_fornecedor = request.form.get("cliente_fornecedor", "").strip()
        nota.valor = parse_valor(request.form.get("valor"))
        nota.data_emissao = parse_data(request.form.get("data_emissao"), nota.data_emissao)
        nota.descricao = request.form.get("descricao", "").strip()

        novo_arquivo = request.files.get("arquivo")
        if novo_arquivo and novo_arquivo.filename:
            if not arquivo_permitido(novo_arquivo.filename):
                flash("Formato não permitido. Envie PDF, JPG, PNG ou WEBP.", "danger")
                return redirect(url_for("notas.editar", nota_id=nota.id))
            caminho_antigo = os.path.join(current_app.config["UPLOAD_FOLDER"], nota.arquivo_nome)
            if os.path.exists(caminho_antigo):
                os.remove(caminho_antigo)
            nota.arquivo_nome_original = novo_arquivo.filename
            nota.arquivo_nome = salvar_arquivo(novo_arquivo)

        db.session.commit()
        flash("Nota atualizada.", "success")
        return redirect(url_for("notas.dashboard"))

    return render_template("editar_nota.html", nota=nota)


@notas_bp.route("/notas/<int:nota_id>/excluir", methods=["POST"])
@login_required
def excluir(nota_id):
    nota = Nota.query.get_or_404(nota_id)
    if not nota.pode_editar(current_user):
        abort(403)

    caminho = os.path.join(current_app.config["UPLOAD_FOLDER"], nota.arquivo_nome)
    if os.path.exists(caminho):
        os.remove(caminho)

    db.session.delete(nota)
    db.session.commit()
    flash("Nota excluída.", "info")
    return redirect(url_for("notas.dashboard"))


@notas_bp.route("/notas/<int:nota_id>/arquivo")
@login_required
def baixar_arquivo(nota_id):
    nota = Nota.query.get_or_404(nota_id)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        nota.arquivo_nome,
        as_attachment=False,
        download_name=nota.arquivo_nome_original,
    )

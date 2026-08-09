# Sistema de Notas Fiscais (Flask + Railway)

Sistema web para enviar e organizar notas fiscais (PDF ou foto) da empresa,
com acesso multiusuário e uso pelo celular. Pensado para deploy no Railway
com Postgres (metadados) + Volume (arquivos).

## Funcionalidades

- Login multiusuário (administradores e funcionários).
- Upload de nota (PDF/JPG/PNG/WEBP) com valor, data, cliente/fornecedor,
  categoria, tipo (entrada/saída) e número da nota.
- No celular, o campo de upload abre a câmera direto (`capture="environment"`).
- Dashboard com filtros (período, tipo, categoria, busca) e totais
  (entradas, saídas, saldo).
- Edição e exclusão de notas (dono da nota ou administrador).
- Gestão de usuários (somente administrador).

## Rodando localmente

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # ajuste se quiser
export $(cat .env | xargs)       # Windows: defina as variáveis manualmente

flask --app wsgi init-db         # cria as tabelas (usa SQLite local por padrão)
flask --app wsgi criar-admin     # cria o primeiro usuário administrador

python wsgi.py                   # http://localhost:5000
```

## Deploy no Railway

1. **Criar o projeto**: no Railway, crie um novo projeto a partir deste
   repositório (conecte o GitHub ou use `railway up` via CLI).

2. **Adicionar Postgres**: no projeto, clique em "New" → "Database" →
   "PostgreSQL". O Railway cria automaticamente a variável `DATABASE_URL`
   e injeta no serviço web (se estiverem no mesmo projeto/ambiente).

3. **Adicionar um Volume** (para guardar os arquivos das notas):
   - No serviço web, vá em "Settings" → "Volumes" → "New Volume".
   - Monte em um caminho, por exemplo `/data`.
   - Defina a variável de ambiente `UPLOAD_FOLDER=/data/uploads`.
   - Sem isso, os arquivos enviados seriam perdidos a cada novo deploy.

4. **Variáveis de ambiente** (Settings → Variables):
   - `SECRET_KEY`: uma string aleatória longa (ex.: gere com
     `python -c "import secrets; print(secrets.token_hex(32))"`).
   - `DATABASE_URL`: já vem preenchida automaticamente pelo Postgres.
   - `UPLOAD_FOLDER`: `/data/uploads` (ou o caminho do seu Volume).

5. **Deploy**: o Railway detecta o `Procfile`/`railway.json` e builda
   automaticamente com Nixpacks (não precisa de Dockerfile).

6. **Inicializar o banco** (uma única vez, após o primeiro deploy):
   ```bash
   railway run flask --app wsgi init-db
   railway run flask --app wsgi criar-admin
   ```
   (o comando `railway run` executa dentro do ambiente do serviço já no ar)

7. **Acessar pelo celular**: use a URL pública gerada pelo Railway
   (Settings → Networking → Generate Domain). Como o layout é responsivo,
   funciona direto no navegador do celular — não precisa instalar nada.
   Se quiser um atalho na tela inicial, "Adicionar à tela de início" no
   Chrome/Safari já dá uma experiência parecida com app.

## Estrutura do projeto

```
notas-fiscais-app/
├── app/
│   ├── __init__.py      # app factory, extensões, CLI (init-db, criar-admin)
│   ├── models.py        # User, Nota
│   ├── auth.py          # login/logout + gestão de usuários
│   ├── notas.py         # upload, dashboard, editar, excluir, download
│   ├── templates/        # HTML (Bootstrap 5, responsivo)
│   └── static/css/
├── config.py             # config (Postgres/SQLite, upload folder, limites)
├── wsgi.py                # ponto de entrada (gunicorn)
├── requirements.txt
├── Procfile
├── railway.json
└── .env.example
```

## Próximos passos sugeridos

- Paginação na listagem quando o volume de notas crescer.
- Exportar relatório em Excel/PDF por período (dá pra usar as skins de
  xlsx/pdf se você tiver esse fluxo em outra ferramenta).
- Backup periódico do Volume/Postgres (Railway tem backups automáticos
  de Postgres nos planos pagos — vale conferir no painel).
- Se depois quiser AWS/GCP, o único ponto acoplado ao Railway é o
  `UPLOAD_FOLDER` (Volume). Trocar por S3/Cloud Storage é uma mudança
  isolada em `app/notas.py` (`salvar_arquivo` e `baixar_arquivo`).

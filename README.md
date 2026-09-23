# P1Garrido — Cardápio Digital

Projeto da disciplina Laboratório de Programação Full Stack — Engenharia de Software (Universidade de Vassouras).

## Tema

**Cardápio Digital** — comanda por mesa com fechamento de conta.

Entidades: Prato, Combo, Mesa, Comanda, Item (ItemComanda).

## Escopo do P1

- Cadastro completo (CRUD) de Pratos e Combos.
- Cadastro de Mesas, com abertura de comanda vinculada à mesa.
- Lançamento de itens (pratos/combos) na comanda aberta.
- Fechamento de conta, com cálculo automático do total.

As features adicionais (busca/filtro e validação de preço) estão explicadas em [RELATORIO.md](RELATORIO.md).

## Como rodar localmente

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_dados   # popula mesas, pratos e combos de exemplo
python manage.py createsuperuser
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/` para o cardápio e `http://127.0.0.1:8000/admin/` para o painel administrativo.

## Stack

Django, SQLite (padrão em desenvolvimento), python-dotenv.

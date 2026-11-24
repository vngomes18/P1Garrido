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

## P2 — Mini-SaaS

A P2 evolui o **mesmo projeto**, sobre a base da P1, com os quatro pilares das Aulas 13, 14 e 17:

| Pilar | O que tem | Onde está |
|-------|-----------|-----------|
| **Multi-organização** | `Organizacao`, base abstrata `DaOrganizacao` (FK em todos os models), migração em 3 etapas sem perder dados da P1, unicidade por organização | `core/models.py`, `cardapio/migrations/0003`–`0005` |
| **Perfis de acesso** | `Perfil` (usuário → organização + papel `admin`/`operador`), login/logout, permissões por papel nas telas e na API | `core/models.py`, `core/permissions.py` |
| **API REST (DRF)** | Serializers com `fields` explícitos, views *generics*, URLs em `/api/`, validação reaproveitada da P1, isolamento por organização | `cardapio/serializers.py`, `api_views.py`, `api_urls.py` |
| **Dashboard** | KPIs (`aggregate`), ranking (`values`+`annotate`), série por mês (`TruncMonth`), distribuição, filtro de período validado, gráficos com Chart.js, exportação CSV e API | `cardapio/dashboard.py`, `templates/cardapio/dashboard.html`, `static/js/` |

### Papéis

| Ação | Administrador | Operador |
|------|:---:|:---:|
| Ver pratos, combos, mesas, comandas e cardápio | ✔ | ✔ |
| Criar/editar/excluir pratos, combos e mesas (telas e API) | ✔ | ✘ (403) |
| Abrir comanda, lançar/remover itens, fechar conta | ✔ | ✔ |
| Dashboard: KPIs, ranking e distribuição | ✔ | ✔ |
| Dashboard: série por mês e **exportar CSV** | ✔ | ✘ |

Quem está logado **sem Perfil** (um superusuário recém-criado, por exemplo) recebe uma página 403 explicando o que falta, em vez de erro 500.
O cardápio público (`/cardapio/<slug>/`, ideal para o QR code da mesa) é a única página sem login e mostra só os itens disponíveis daquela organização.

### API

Autenticação por sessão do Django (a Browsable API aceita login em `/api-auth/login/`). Sem login a resposta é 403.

| Recurso | Endereços | Observação |
|---------|-----------|------------|
| Pratos | `GET/POST /api/pratos/` · `GET/PUT/PATCH/DELETE /api/pratos/<id>/` | filtros `?q=` e `?categoria=` |
| Combos | `/api/combos/` · `/api/combos/<id>/` | regra do desconto de 10% a 15% |
| Mesas | `/api/mesas/` · `/api/mesas/<id>/` | número único por organização |
| Comandas | `GET/POST /api/comandas/` · `GET /api/comandas/<id>/` | `POST` abre a comanda; filtro `?status=` |
| Itens | `POST /api/comandas/<id>/itens/` · `DELETE /api/itens/<id>/` | só em comanda aberta |
| Fechar conta | `POST /api/comandas/<id>/fechar/` | calcula o total |
| Dashboard | `GET /api/dashboard/?inicio=AAAA-MM-DD&fim=AAAA-MM-DD` | mesmas métricas da tela |

Erros: `400` dado inválido · `403` sem permissão · `404` não existe (inclusive registro de **outra** organização) · `409` registro em uso.

Para testar: abra `http://127.0.0.1:8000/api/pratos/` no navegador já logado (a Browsable API mostra os dados e traz formulário para `POST`),
ou use `curl -b cookies.txt http://127.0.0.1:8000/api/pratos/` com o cookie de sessão.

### Roteiro de isolamento (Aula 14)

Dois usuários, duas organizações, executado de forma **automatizada** em `cardapio/test_isolamento.py` e `cardapio/test_api.py`:

| Cenário | Resultado esperado | Resultado |
|---------|--------------------|:---:|
| Usuário A abre a lista de pratos/combos/mesas/comandas | Vê só os da organização A | ✔ passou |
| Usuário A abre `/pratos/<id-da-B>/editar/` (e combos, mesas, comandas, itens) | 404 | ✔ passou |
| Usuário A cria um prato | Gravado na organização A, mesmo se o formulário enviar outra | ✔ passou |
| Selects dos formulários (pratos do combo, item da comanda) | Só opções da organização A | ✔ passou |
| Usuário A cadastra mesa com número que a B já usa | Permitido (unicidade é por organização) | ✔ passou |
| Usuário A cadastra mesa com número que a própria A já usa | Recusado com mensagem, sem `IntegrityError` | ✔ passou |
| Mesmos cenários pela API (`/api/...`) e no dashboard/CSV | Nenhum dado da B aparece | ✔ passou |

## Como rodar localmente

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_dados   # 2 organizações, usuários, mesas, pratos, combos e histórico de comandas
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/` (login) e `http://127.0.0.1:8000/admin/` (painel administrativo).

Usuários criados pelo `seed_dados` (senha **`senha1234`**, apenas para desenvolvimento):

| Organização | Administrador | Operador |
|-------------|---------------|----------|
| Burger House | `ana` | `ana.op` |
| Cantina Bella | `bruno` | `bruno.op` |

Para criar o seu próprio acesso: `python manage.py createsuperuser`, e depois, no Admin, crie uma **Organização** e um **Perfil** ligando o usuário a ela
(o superusuário não precisa de perfil para usar o Admin, mas precisa dele para usar as telas do sistema).

> **Dados da P1:** ao rodar `migrate` em um banco que já tem registros da P1, eles são movidos automaticamente para a "Organizacao padrao"
> (migração de dados `0004_dados_org`). Faça um backup do `db.sqlite3` antes, por precaução.

## Testes

```powershell
python manage.py test
```

118 testes: regras da P1, isolamento entre organizações, papéis, API, métricas do dashboard (com números conferidos à mão) e proteção contra N+1 (`assertNumQueries`).

## Stack

Django 6.1, Django REST Framework, SQLite (padrão em desenvolvimento) ou PostgreSQL via `.env`, python-dotenv, Chart.js (arquivo local em `static/js/`).

Documentos de apoio: [RELATORIO.md](RELATORIO.md) (features da P1) e [MELHORIAS_P1.md](MELHORIAS_P1.md) (revisão da P1 feita na Aula 13).

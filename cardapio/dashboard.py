"""Metricas do dashboard calculadas pelo ORM (Aula 17).

Toda metrica parte de um queryset ja filtrado pela ORGANIZACAO e pelo PERIODO.
As mesmas funcoes alimentam a tela, o CSV e a API (nada de consulta duplicada).
"""
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth

from .forms import PeriodoForm
from .models import Comanda, ItemComanda, Prato

ZERO = Value(Decimal('0.00'), output_field=DecimalField(max_digits=11, decimal_places=2))
CENTAVO = Decimal('0.01')


def filtrar_periodo(params, qs, campo):
    """Aplica ?inicio=AAAA-MM-DD&fim=AAAA-MM-DD ao campo de data. Datas invalidas sao ignoradas."""
    form = PeriodoForm(params)
    if form.is_valid():
        inicio, fim = form.cleaned_data['inicio'], form.cleaned_data['fim']
        if inicio:
            qs = qs.filter(**{f'{campo}__date__gte': inicio})
        if fim:
            qs = qs.filter(**{f'{campo}__date__lte': fim})
    return qs


def comandas_base(org, params):
    return filtrar_periodo(params, Comanda.objects.filter(organizacao=org), 'aberta_em')


def itens_base(org, params):
    return filtrar_periodo(params, ItemComanda.objects.filter(organizacao=org), 'comanda__aberta_em')


# 1) KPIs: aggregate -> UM dicionario com os totais
def kpis(org, params):
    fechada = Q(status=Comanda.Status.FECHADA)
    # Cuidado: o alias NAO pode ter o nome de um campo do model (Comanda.total).
    dados = comandas_base(org, params).aggregate(
        comandas=Count('id'),
        abertas=Count('id', filter=Q(status=Comanda.Status.ABERTA)),
        fechadas=Count('id', filter=fechada),
        faturamento=Coalesce(Sum('total', filter=fechada), ZERO),
        ticket_medio=Avg('total', filter=fechada),
    )
    dados['faturamento'] = Decimal(dados['faturamento']).quantize(CENTAVO)
    dados['ticket_medio'] = Decimal(dados['ticket_medio'] or 0).quantize(CENTAVO)
    return dados


# 2) Ranking: values + annotate + order_by (agrupa, conta, ordena, fatia)
def ranking_itens(org, params, limite=5):
    return list(
        itens_base(org, params)
        .annotate(nome_item=Coalesce('prato__nome', 'combo__nome'))
        .values('nome_item')
        .annotate(total=Sum('quantidade'))
        .order_by('-total', 'nome_item')[:limite]
    )


# 3) Serie no tempo: faturamento por mes (TruncMonth + order_by para o grafico nao embaralhar)
def faturamento_por_mes(org, params):
    qs = (
        comandas_base(org, params)
        .filter(status=Comanda.Status.FECHADA)
        .annotate(mes=TruncMonth('fechada_em'))
        .values('mes')
        .annotate(faturamento=Sum('total'), comandas=Count('id'))
        .order_by('mes')
    )
    return [
        {'mes': linha['mes'].strftime('%m/%Y'), 'total': float(linha['faturamento']), 'comandas': linha['comandas']}
        for linha in qs
    ]


# 4) Distribuicao: itens vendidos por categoria (combos formam a sua propria fatia)
def vendas_por_categoria(org, params):
    rotulos = dict(Prato.Categoria.choices)
    rotulos['COMBO'] = 'Combos'
    qs = (
        itens_base(org, params)
        .annotate(categoria=Coalesce('prato__categoria', Value('COMBO')))
        .values('categoria')
        .annotate(total=Sum('quantidade'))
        .order_by('-total', 'categoria')
    )
    return [{'categoria': rotulos[linha['categoria']], 'total': linha['total']} for linha in qs]


def resumo(org, params, incluir_series=True):
    """Tudo junto (usado pela tela e pela API). Series mensais so para quem pode ver."""
    dados = {
        'kpis': kpis(org, params),
        'ranking': ranking_itens(org, params),
        'por_categoria': vendas_por_categoria(org, params),
    }
    if incluir_series:
        dados['por_mes'] = faturamento_por_mes(org, params)
    return dados

"""Metricas do dashboard (Aula 17). Dados conhecidos, conferiveis a mao:

Org A (3 comandas fechadas)                       total
  c1  15/01/2026  1x Prato 10                      10.00
  c2  10/02/2026  2x Prato 10 + 1x Combo (8.00)    28.00
  c3  20/02/2026  3x Prato 10 + 2x Suco (5.00)     40.00
  -> faturamento 78.00 | ticket medio 26.00 | mes 01/2026 = 10.00 | mes 02/2026 = 68.00
Org B: 5 comandas de 7.00.
"""
import csv
import io
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.urls import reverse

from core.models import Organizacao, Perfil
from core.testing import DuasOrganizacoesMixin, criar_usuario

from .models import Combo, Comanda, ItemComanda, Mesa, Prato
from .views import _celula_segura

FUSO = ZoneInfo('America/Sao_Paulo')


def comanda_fechada(org, mesa, itens, quando):
    comanda = Comanda.objects.create(organizacao=org, mesa=mesa)
    for produto, quantidade in itens:
        campo = 'prato' if isinstance(produto, Prato) else 'combo'
        ItemComanda.objects.create(comanda=comanda, quantidade=quantidade, **{campo: produto})
    comanda.fechar()
    # auto_now_add ignora valores na criacao: ajustamos a data por update.
    Comanda.objects.filter(pk=comanda.pk).update(aberta_em=quando, fechada_em=quando)
    return comanda


class DashboardBase(DuasOrganizacoesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        mesa = Mesa.objects.create(organizacao=cls.org_a, numero=1)
        p10 = Prato.objects.create(organizacao=cls.org_a, nome='Prato 10', preco=Decimal('10.00'))
        suco = Prato.objects.create(organizacao=cls.org_a, nome='Suco', preco=Decimal('5.00'),
                                    categoria=Prato.Categoria.BEBIDA)
        combo = Combo.objects.create(organizacao=cls.org_a, nome='Combo', preco=Decimal('8.00'))
        comanda_fechada(cls.org_a, mesa, [(p10, 1)], datetime(2026, 1, 15, 12, tzinfo=FUSO))
        comanda_fechada(cls.org_a, mesa, [(p10, 2), (combo, 1)], datetime(2026, 2, 10, 12, tzinfo=FUSO))
        comanda_fechada(cls.org_a, mesa, [(p10, 3), (suco, 2)], datetime(2026, 2, 20, 12, tzinfo=FUSO))

        mesa_b = Mesa.objects.create(organizacao=cls.org_b, numero=1)
        prato_b = Prato.objects.create(organizacao=cls.org_b, nome='Prato B', preco=Decimal('7.00'))
        for dia in range(1, 6):
            comanda_fechada(cls.org_b, mesa_b, [(prato_b, 1)], datetime(2026, 2, dia, 12, tzinfo=FUSO))

    def dashboard(self, **params):
        return self.client.get(reverse('dashboard'), params)


class MetricasTests(DashboardBase):
    def test_total_da_organizacao(self):
        self.assertEqual(self.dashboard().context['kpis']['comandas'], 3)
        self.client.force_login(self.admin_b)
        self.assertEqual(self.dashboard().context['kpis']['comandas'], 5)

    def test_kpis_faturamento_e_ticket_medio(self):
        kpis = self.dashboard().context['kpis']
        self.assertEqual(kpis['faturamento'], Decimal('78.00'))
        self.assertEqual(kpis['ticket_medio'], Decimal('26.00'))
        self.assertEqual((kpis['abertas'], kpis['fechadas']), (0, 3))

    def test_comandas_abertas_contam_em_abertas_mas_nao_no_faturamento(self):
        Comanda.objects.create(organizacao=self.org_a, mesa=Mesa.objects.get(organizacao=self.org_a))
        kpis = self.dashboard().context['kpis']
        self.assertEqual((kpis['comandas'], kpis['abertas'], kpis['fechadas']), (4, 1, 3))
        self.assertEqual(kpis['faturamento'], Decimal('78.00'))

    def test_ranking_de_itens_ordenado_e_com_combo(self):
        ranking = self.dashboard().context['ranking']
        self.assertEqual([(r['nome_item'], r['total']) for r in ranking],
                         [('Prato 10', 6), ('Suco', 2), ('Combo', 1)])

    def test_distribuicao_por_categoria(self):
        dados = self.dashboard().context['por_categoria']
        self.assertEqual([(d['categoria'], d['total']) for d in dados],
                         [('Prato principal', 6), ('Bebida', 2), ('Combos', 1)])

    def test_serie_por_mes_em_ordem_cronologica(self):
        serie = self.dashboard().context['por_mes']
        self.assertEqual([(s['mes'], s['total'], s['comandas']) for s in serie],
                         [('01/2026', 10.0, 1), ('02/2026', 68.0, 2)])

    def test_dados_do_grafico_chegam_ao_template_via_json_script(self):
        resp = self.dashboard()
        self.assertContains(resp, 'id="dados-mes"')
        self.assertContains(resp, 'id="dados-categoria"')
        self.assertContains(resp, 'js/chart.umd.js')
        self.assertContains(resp, 'js/dashboard.js')


class PeriodoTests(DashboardBase):
    def test_periodo_filtra_todas_as_metricas(self):
        resp = self.dashboard(inicio='2026-02-01', fim='2026-02-28')
        self.assertEqual(resp.context['kpis']['comandas'], 2)
        self.assertEqual(resp.context['kpis']['faturamento'], Decimal('68.00'))
        self.assertEqual([r['nome_item'] for r in resp.context['ranking']], ['Prato 10', 'Suco', 'Combo'])
        self.assertEqual(resp.context['ranking'][0]['total'], 5)
        self.assertEqual([s['mes'] for s in resp.context['por_mes']], ['02/2026'])

    def test_somente_inicio_ou_somente_fim(self):
        self.assertEqual(self.dashboard(inicio='2026-02-20').context['kpis']['comandas'], 1)
        self.assertEqual(self.dashboard(fim='2026-01-31').context['kpis']['comandas'], 1)

    def test_limites_do_periodo_sao_inclusivos(self):
        self.assertEqual(self.dashboard(inicio='2026-02-10', fim='2026-02-10').context['kpis']['comandas'], 1)

    def test_data_invalida_na_url_nao_gera_erro_500(self):
        resp = self.dashboard(inicio='abc', fim='31/12/2026')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['kpis']['comandas'], 3)  # filtro ignorado
        self.assertTrue(resp.context['form'].errors)

    def test_inicio_depois_do_fim_mostra_erro_e_ignora_o_filtro(self):
        resp = self.dashboard(inicio='2026-03-01', fim='2026-01-01')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'A data inicial nao pode ser depois da data final.')
        self.assertEqual(resp.context['kpis']['comandas'], 3)

    def test_periodo_sem_dados_nao_quebra(self):
        resp = self.dashboard(inicio='2030-01-01')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['kpis']['comandas'], 0)
        self.assertEqual(resp.context['kpis']['faturamento'], Decimal('0.00'))
        self.assertEqual(resp.context['kpis']['ticket_medio'], Decimal('0.00'))
        self.assertContains(resp, 'Sem dados no periodo.')
        self.assertContains(resp, 'Sem comandas fechadas no periodo.')


class DashboardVazioTests(TestCase):
    def test_organizacao_nova_sem_nenhum_dado(self):
        org = Organizacao.objects.create(nome='Recem criada')
        self.client.force_login(criar_usuario('novo', org, Perfil.ADMIN))
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['kpis']['comandas'], 0)
        self.assertEqual(resp.context['ranking'], [])


class ExportacaoCsvTests(DashboardBase):
    def linhas(self, **params):
        resp = self.client.get(reverse('exportar_csv'), params)
        self.assertEqual(resp.status_code, 200)
        texto = resp.content.decode('utf-8-sig')
        return list(csv.reader(io.StringIO(texto)))

    def test_csv_tem_so_as_comandas_da_organizacao(self):
        linhas = self.linhas()
        self.assertEqual(linhas[0], ['Comanda', 'Mesa', 'Status', 'Aberta em', 'Fechada em', 'Itens', 'Total'])
        self.assertEqual(len(linhas) - 1, 3)
        self.assertNotIn('Prato B', ' '.join(' '.join(l) for l in linhas))

    def test_csv_respeita_o_periodo(self):
        self.assertEqual(len(self.linhas(inicio='2026-02-01')) - 1, 2)

    def test_csv_descreve_os_itens_e_o_total(self):
        linha = next(l for l in self.linhas() if l[0] != 'Comanda' and l[-1] == '40.00')
        self.assertEqual(linha[5], '3x Prato 10; 2x Suco')

    def test_numero_de_consultas_nao_cresce_com_o_numero_de_comandas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as poucas:
            self.client.get(reverse('exportar_csv'))
        mesa = Mesa.objects.get(organizacao=self.org_a)
        prato = Prato.objects.get(organizacao=self.org_a, nome='Prato 10')
        for _ in range(6):
            comanda_fechada(self.org_a, mesa, [(prato, 1)], datetime(2026, 2, 25, 12, tzinfo=FUSO))
        with CaptureQueriesContext(connection) as muitas:
            self.client.get(reverse('exportar_csv'))
        self.assertEqual(len(poucas), len(muitas))

    def test_celulas_que_parecem_formula_sao_neutralizadas(self):
        for perigoso in ('=1+1', '+cmd', '-2', '@SUM(A1)'):
            self.assertEqual(_celula_segura(perigoso), "'" + perigoso)
        self.assertEqual(_celula_segura('Mesa 1'), 'Mesa 1')
        self.assertEqual(_celula_segura(None), '')


class ApiDashboardTests(DashboardBase):
    def test_api_devolve_as_mesmas_metricas_da_tela(self):
        api = self.client.get(reverse('api_dashboard')).json()
        tela = self.dashboard().context
        self.assertEqual(api['kpis']['comandas'], tela['kpis']['comandas'])
        self.assertEqual(api['kpis']['faturamento'], '78.00')
        self.assertEqual(api['por_mes'][1], {'mes': '02/2026', 'total': '68.00', 'comandas': 2})
        self.assertEqual([r['nome_item'] for r in api['ranking']], [r['nome_item'] for r in tela['ranking']])

    def test_api_respeita_organizacao_e_periodo(self):
        api = self.client.get(reverse('api_dashboard'), {'inicio': '2026-02-01', 'fim': '2026-02-28'}).json()
        self.assertEqual(api['kpis']['comandas'], 2)
        self.client.force_login(self.admin_b)
        self.assertEqual(self.client.get(reverse('api_dashboard')).json()['kpis']['comandas'], 5)


class DesempenhoTests(DashboardBase):
    """assertNumQueries trava o desempenho: se o N+1 voltar, o teste falha (Aula 17)."""

    def consultas(self, nome):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200)
        return len(ctx)

    def test_lista_de_combos_nao_faz_uma_consulta_por_combo(self):
        pratos = list(Prato.objects.filter(organizacao=self.org_a))
        antes = self.consultas('combo_list')
        for i in range(8):
            Combo.objects.create(organizacao=self.org_a, nome=f'C{i}', preco=Decimal('9.00')).pratos.set(pratos)
        self.assertEqual(self.consultas('combo_list'), antes)

    def test_lista_de_comandas_nao_faz_uma_consulta_por_comanda(self):
        antes = self.consultas('comanda_list')
        mesa = Mesa.objects.get(organizacao=self.org_a)
        prato = Prato.objects.get(organizacao=self.org_a, nome='Prato 10')
        for _ in range(8):
            comanda_fechada(self.org_a, mesa, [(prato, 1)], datetime(2026, 2, 25, 12, tzinfo=FUSO))
        self.assertEqual(self.consultas('comanda_list'), antes)

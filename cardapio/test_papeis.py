"""Perfis de acesso: administrador faz tudo; operador atende (comandas) mas nao altera cadastros."""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.testing import DuasOrganizacoesMixin

from .models import Combo, Comanda, Mesa, Prato


class PapeisTests(DuasOrganizacoesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.prato = Prato.objects.create(organizacao=cls.org_a, nome='X-Burger', preco=Decimal('25.00'))
        cls.combo = Combo.objects.create(organizacao=cls.org_a, nome='Combo', preco=Decimal('20.00'))
        cls.mesa = Mesa.objects.create(organizacao=cls.org_a, numero=1)

    def entrar_como_operador(self):
        self.client.force_login(self.operador_a)

    def test_operador_nao_cria_edita_nem_exclui_cadastros(self):
        self.entrar_como_operador()
        dados = {'nome': 'Novo', 'categoria': 'PRINCIPAL', 'preco': '10.00', 'numero': 9}
        for nome, args in (('prato_create', []), ('combo_create', []), ('mesa_create', []),
                           ('prato_update', [self.prato.pk]), ('prato_delete', [self.prato.pk]),
                           ('combo_update', [self.combo.pk]), ('combo_delete', [self.combo.pk]),
                           ('mesa_update', [self.mesa.pk]), ('mesa_delete', [self.mesa.pk])):
            url = reverse(nome, args=args)
            self.assertEqual(self.client.get(url).status_code, 403, nome)
            self.assertEqual(self.client.post(url, dados).status_code, 403, nome)
        self.assertEqual(Prato.objects.filter(organizacao=self.org_a).count(), 1)
        self.assertEqual(Mesa.objects.filter(organizacao=self.org_a).count(), 1)

    def test_operador_ve_as_listas_sem_os_botoes_de_edicao(self):
        self.entrar_como_operador()
        for nome in ('prato_list', 'combo_list', 'mesa_list'):
            resp = self.client.get(reverse(nome))
            self.assertEqual(resp.status_code, 200, nome)
            self.assertNotContains(resp, '/editar/', msg_prefix=nome)
            self.assertNotContains(resp, '/excluir/', msg_prefix=nome)

    def test_administrador_ve_os_botoes_de_edicao(self):
        resp = self.client.get(reverse('prato_list'))
        self.assertContains(resp, f'/pratos/{self.prato.pk}/editar/')

    def test_operador_atende_abre_lanca_e_fecha_comanda(self):
        self.entrar_como_operador()
        self.client.post(reverse('abrir_comanda', args=[self.mesa.pk]))
        comanda = Comanda.objects.get(mesa=self.mesa)
        resp = self.client.post(reverse('adicionar_item', args=[comanda.pk]), {'prato': self.prato.pk, 'quantidade': 2})
        self.assertEqual(resp.status_code, 302)
        self.client.post(reverse('fechar_comanda', args=[comanda.pk]))
        comanda.refresh_from_db()
        self.assertEqual(comanda.status, Comanda.Status.FECHADA)
        self.assertEqual(comanda.total, Decimal('50.00'))

    def test_operador_nao_exporta_csv(self):
        self.entrar_como_operador()
        self.assertEqual(self.client.get(reverse('exportar_csv')).status_code, 403)

    def test_administrador_exporta_csv(self):
        resp = self.client.get(reverse('exportar_csv'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv; charset=utf-8')

    def test_dashboard_do_operador_e_parcial(self):
        self.entrar_como_operador()
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['mostra_series'])
        self.assertNotIn('por_mes', resp.context)
        self.assertNotContains(resp, 'Exportar CSV')
        self.assertIn('kpis', resp.context)
        self.assertIn('ranking', resp.context)

    def test_dashboard_do_administrador_tem_series_e_exportacao(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertTrue(resp.context['mostra_series'])
        self.assertIn('por_mes', resp.context)
        self.assertContains(resp, 'Exportar CSV')

"""API REST (DRF): autenticacao, permissoes por papel, validacao, isolamento e fluxo da comanda."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from core.testing import DuasOrganizacoesMixin

from .models import Combo, Comanda, ItemComanda, Mesa, Prato


class ApiTestBase(DuasOrganizacoesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.burger = Prato.objects.create(organizacao=cls.org_a, nome='X-Burger', preco=Decimal('25.90'))
        cls.batata = Prato.objects.create(organizacao=cls.org_a, nome='Batata Frita', preco=Decimal('18.50'))
        cls.refri = Prato.objects.create(organizacao=cls.org_a, nome='Refrigerante', preco=Decimal('7.00'))
        cls.prato_b = Prato.objects.create(organizacao=cls.org_b, nome='Prato B', preco=Decimal('30.00'))
        cls.mesa_a = Mesa.objects.create(organizacao=cls.org_a, numero=1)
        cls.mesa_b = Mesa.objects.create(organizacao=cls.org_b, numero=1)

    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.force_authenticate(self.admin_a)


class AutenticacaoTests(ApiTestBase):
    def test_sem_login_a_api_nega_acesso(self):
        anonimo = APIClient()
        for nome in ('api_prato_list', 'api_combo_list', 'api_mesa_list', 'api_comanda_list', 'api_dashboard'):
            self.assertIn(anonimo.get(reverse(nome)).status_code, (401, 403), nome)
        resp = anonimo.post(reverse('api_prato_list'), {'nome': 'X', 'preco': '10'}, format='json')
        self.assertIn(resp.status_code, (401, 403))
        self.assertFalse(Prato.objects.filter(nome='X').exists())

    def test_usuario_sem_perfil_nao_acessa(self):
        sem_perfil = User.objects.create_superuser('root', password='x')
        cliente = APIClient()
        cliente.force_authenticate(sem_perfil)
        self.assertEqual(cliente.get(reverse('api_prato_list')).status_code, 403)

    def test_autenticacao_por_sessao_do_django(self):
        cliente = APIClient()
        cliente.force_login(self.admin_a)
        self.assertEqual(cliente.get(reverse('api_prato_list')).status_code, 200)


class PratoApiTests(ApiTestBase):
    def test_crud_completo_em_json(self):
        resp = self.api.post(reverse('api_prato_list'), {
            'nome': 'Brownie', 'categoria': 'SOBREMESA', 'preco': '16.00'}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(set(resp.json()), {'id', 'nome', 'descricao', 'categoria', 'preco', 'disponivel'})
        pk = resp.json()['id']
        self.assertEqual(Prato.objects.get(pk=pk).organizacao, self.org_a)

        resp = self.api.get(reverse('api_prato_detail', args=[pk]))
        self.assertEqual((resp.status_code, resp.json()['nome']), (200, 'Brownie'))

        resp = self.api.patch(reverse('api_prato_detail', args=[pk]), {'preco': '18.00'}, format='json')
        self.assertEqual((resp.status_code, resp.json()['preco']), (200, '18.00'))

        resp = self.api.delete(reverse('api_prato_detail', args=[pk]))
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Prato.objects.filter(pk=pk).exists())

    def test_a_regra_de_preco_da_p1_vale_na_api(self):
        for preco in ('0', '-5.00'):
            resp = self.api.post(reverse('api_prato_list'), {'nome': 'Ruim', 'preco': preco}, format='json')
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json()['preco'], ['O preco do prato deve ser maior que zero.'])
        self.assertFalse(Prato.objects.filter(nome='Ruim').exists())

    def test_busca_e_filtro_por_categoria(self):
        resp = self.api.get(reverse('api_prato_list'), {'q': 'burger'})
        self.assertEqual([p['nome'] for p in resp.json()], ['X-Burger'])
        self.burger.categoria = Prato.Categoria.BEBIDA
        self.burger.save()
        resp = self.api.get(reverse('api_prato_list'), {'categoria': 'BEBIDA'})
        self.assertEqual([p['nome'] for p in resp.json()], ['X-Burger'])

    def test_prato_em_uso_responde_409(self):
        comanda = Comanda.objects.create(organizacao=self.org_a, mesa=self.mesa_a)
        ItemComanda.objects.create(comanda=comanda, prato=self.burger, quantidade=1)
        resp = self.api.delete(reverse('api_prato_detail', args=[self.burger.pk]))
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(Prato.objects.filter(pk=self.burger.pk).exists())

    def test_resposta_nao_expoe_a_organizacao(self):
        for prato in self.api.get(reverse('api_prato_list')).json():
            self.assertNotIn('organizacao', prato)


class IsolamentoApiTests(ApiTestBase):
    def test_lista_so_tem_dados_da_organizacao(self):
        nomes = [p['nome'] for p in self.api.get(reverse('api_prato_list')).json()]
        self.assertNotIn('Prato B', nomes)
        self.assertEqual(len(nomes), 3)

    def test_detalhe_alterar_e_excluir_de_outra_organizacao_dao_404(self):
        url = reverse('api_prato_detail', args=[self.prato_b.pk])
        self.assertEqual(self.api.get(url).status_code, 404)
        self.assertEqual(self.api.patch(url, {'nome': 'Invadido'}, format='json').status_code, 404)
        self.assertEqual(self.api.delete(url).status_code, 404)
        self.prato_b.refresh_from_db()
        self.assertEqual(self.prato_b.nome, 'Prato B')

    def test_organizacao_enviada_no_corpo_e_ignorada(self):
        resp = self.api.post(reverse('api_prato_list'), {
            'nome': 'Tentativa', 'preco': '10.00', 'organizacao': self.org_b.pk}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Prato.objects.get(nome='Tentativa').organizacao, self.org_a)

    def test_combo_com_prato_de_outra_organizacao_e_rejeitado(self):
        resp = self.api.post(reverse('api_combo_list'), {
            'nome': 'Combo', 'preco': '27.00', 'pratos': [self.prato_b.pk]}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('pratos', resp.json())

    def test_item_com_prato_de_outra_organizacao_e_rejeitado(self):
        comanda = Comanda.objects.create(organizacao=self.org_a, mesa=self.mesa_a)
        resp = self.api.post(reverse('api_item_create', args=[comanda.pk]), {
            'prato': self.prato_b.pk, 'quantidade': 1}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(comanda.itens.exists())

    def test_comanda_de_outra_organizacao_da_404(self):
        comanda_b = Comanda.objects.create(organizacao=self.org_b, mesa=self.mesa_b)
        self.assertEqual(self.api.get(reverse('api_comanda_detail', args=[comanda_b.pk])).status_code, 404)
        self.assertEqual(self.api.post(reverse('api_comanda_fechar', args=[comanda_b.pk])).status_code, 404)
        self.assertEqual(self.api.post(reverse('api_item_create', args=[comanda_b.pk]), {
            'prato': self.burger.pk, 'quantidade': 1}, format='json').status_code, 404)

    def test_abrir_comanda_em_mesa_de_outra_organizacao_e_rejeitado(self):
        resp = self.api.post(reverse('api_comanda_list'), {'mesa': self.mesa_b.pk}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(Comanda.objects.filter(mesa=self.mesa_b).exists())

    def test_mesa_com_mesmo_numero_em_outra_organizacao_e_permitida_mas_nao_na_propria(self):
        self.assertEqual(self.api.post(reverse('api_mesa_list'), {'numero': 2, 'capacidade': 4}, format='json').status_code, 201)
        resp = self.api.post(reverse('api_mesa_list'), {'numero': 1, 'capacidade': 4}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['numero'], ['Ja existe uma mesa com este numero.'])


class ComboApiTests(ApiTestBase):
    # Soma dos pratos: 25.90 + 18.50 + 7.00 = 51.40 -> faixa permitida de 43.69 a 46.26
    def corpo(self, preco):
        return {'nome': 'Combo X-Burger', 'preco': preco, 'pratos': [self.burger.pk, self.batata.pk, self.refri.pk]}

    def test_preco_dentro_da_faixa_e_aceito(self):
        resp = self.api.post(reverse('api_combo_list'), self.corpo('45.00'), format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(sorted(resp.json()['pratos']), sorted([self.burger.pk, self.batata.pk, self.refri.pk]))

    def test_desconto_fora_da_faixa_e_rejeitado_com_a_mensagem_da_p1(self):
        for preco in ('51.40', '46.27', '43.68'):
            resp = self.api.post(reverse('api_combo_list'), self.corpo(preco), format='json')
            self.assertEqual(resp.status_code, 400, preco)
            self.assertIn('entre R$ 43.69 e R$ 46.26', resp.json()['preco'][0])

    def test_preco_zero_e_rejeitado_uma_unica_vez(self):
        resp = self.api.post(reverse('api_combo_list'), self.corpo('0'), format='json')
        self.assertEqual(resp.json()['preco'], ['O preco do combo deve ser maior que zero.'])

    def test_combo_sem_pratos_e_rejeitado(self):
        resp = self.api.post(reverse('api_combo_list'), {'nome': 'Vazio', 'preco': '10.00', 'pratos': []}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_atualizacao_parcial_revalida_o_desconto(self):
        combo = Combo.objects.create(organizacao=self.org_a, nome='C', preco=Decimal('45.00'))
        combo.pratos.set([self.burger, self.batata, self.refri])
        resp = self.api.patch(reverse('api_combo_detail', args=[combo.pk]), {'preco': '50.00'}, format='json')
        self.assertEqual(resp.status_code, 400)
        resp = self.api.patch(reverse('api_combo_detail', args=[combo.pk]), {'preco': '44.00'}, format='json')
        self.assertEqual(resp.status_code, 200)


class PapeisApiTests(ApiTestBase):
    def test_operador_le_mas_nao_escreve_cadastros(self):
        self.api.force_authenticate(self.operador_a)
        self.assertEqual(self.api.get(reverse('api_prato_list')).status_code, 200)
        self.assertEqual(self.api.get(reverse('api_mesa_list')).status_code, 200)
        self.assertEqual(self.api.post(reverse('api_prato_list'), {'nome': 'X', 'preco': '10'}, format='json').status_code, 403)
        self.assertEqual(self.api.delete(reverse('api_prato_detail', args=[self.burger.pk])).status_code, 403)
        self.assertEqual(self.api.post(reverse('api_mesa_list'), {'numero': 7, 'capacidade': 2}, format='json').status_code, 403)
        self.assertTrue(Prato.objects.filter(pk=self.burger.pk).exists())

    def test_operador_opera_comandas(self):
        self.api.force_authenticate(self.operador_a)
        resp = self.api.post(reverse('api_comanda_list'), {'mesa': self.mesa_a.pk}, format='json')
        self.assertEqual(resp.status_code, 201)

    def test_dashboard_do_operador_nao_traz_series(self):
        self.api.force_authenticate(self.operador_a)
        self.assertNotIn('por_mes', self.api.get(reverse('api_dashboard')).json())
        self.api.force_authenticate(self.admin_a)
        self.assertIn('por_mes', self.api.get(reverse('api_dashboard')).json())


class ComandaApiTests(ApiTestBase):
    def test_fluxo_completo_abrir_lancar_e_fechar(self):
        resp = self.api.post(reverse('api_comanda_list'), {'mesa': self.mesa_a.pk}, format='json')
        self.assertEqual(resp.status_code, 201)
        comanda_id = resp.json()['id']
        self.assertEqual(resp.json()['status'], 'ABERTA')

        resp = self.api.post(reverse('api_item_create', args=[comanda_id]), {
            'prato': self.burger.pk, 'quantidade': 2}, format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()['subtotal'], '51.80')
        item_id = resp.json()['id']

        resp = self.api.get(reverse('api_comanda_detail', args=[comanda_id]))
        self.assertEqual(len(resp.json()['itens']), 1)

        resp = self.api.post(reverse('api_comanda_fechar', args=[comanda_id]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual((resp.json()['status'], resp.json()['total']), ('FECHADA', '51.80'))

        # comanda fechada nao aceita mais mudancas
        resp = self.api.post(reverse('api_item_create', args=[comanda_id]), {'prato': self.refri.pk, 'quantidade': 1}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(self.api.delete(reverse('api_item_detail', args=[item_id])).status_code, 400)
        self.assertEqual(self.api.post(reverse('api_comanda_fechar', args=[comanda_id])).status_code, 400)

    def test_remover_item_de_comanda_aberta(self):
        comanda = Comanda.objects.create(organizacao=self.org_a, mesa=self.mesa_a)
        item = ItemComanda.objects.create(comanda=comanda, prato=self.burger, quantidade=1)
        self.assertEqual(self.api.delete(reverse('api_item_detail', args=[item.pk])).status_code, 204)
        self.assertFalse(comanda.itens.exists())

    def test_mesa_so_pode_ter_uma_comanda_aberta(self):
        Comanda.objects.create(organizacao=self.org_a, mesa=self.mesa_a)
        resp = self.api.post(reverse('api_comanda_list'), {'mesa': self.mesa_a.pk}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_item_precisa_de_prato_ou_combo_e_quantidade_positiva(self):
        comanda = Comanda.objects.create(organizacao=self.org_a, mesa=self.mesa_a)
        url = reverse('api_item_create', args=[comanda.pk])
        self.assertEqual(self.api.post(url, {'quantidade': 1}, format='json').status_code, 400)
        self.assertEqual(self.api.post(url, {'prato': self.burger.pk, 'quantidade': 0}, format='json').status_code, 400)

    def test_filtro_por_status(self):
        Comanda.objects.create(organizacao=self.org_a, mesa=self.mesa_a)
        fechada = Comanda.objects.create(organizacao=self.org_a, mesa=Mesa.objects.create(organizacao=self.org_a, numero=2))
        fechada.fechar()
        self.assertEqual(len(self.api.get(reverse('api_comanda_list'), {'status': 'FECHADA'}).json()), 1)
        self.assertEqual(len(self.api.get(reverse('api_comanda_list')).json()), 2)

    def test_listagem_nao_faz_n_mais_1(self):
        for numero in range(2, 7):
            mesa = Mesa.objects.create(organizacao=self.org_a, numero=numero)
            comanda = Comanda.objects.create(organizacao=self.org_a, mesa=mesa)
            ItemComanda.objects.create(comanda=comanda, prato=self.burger, quantidade=1)
        # sessao/usuario nao contam (force_authenticate); sobram: comandas+mesa, itens+prato+combo
        with self.assertNumQueries(2):
            self.api.get(reverse('api_comanda_list'))

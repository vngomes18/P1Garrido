"""Roteiro de isolamento da Aula 14: dois usuarios, duas organizacoes, nenhum vazamento."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Perfil
from core.testing import DuasOrganizacoesMixin

from .forms import ComboForm, ItemComandaForm
from .models import Combo, Comanda, ItemComanda, Mesa, Prato


class IsolamentoTestBase(DuasOrganizacoesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.prato_a = Prato.objects.create(organizacao=cls.org_a, nome='Prato A', preco=Decimal('20.00'))
        cls.prato_b = Prato.objects.create(organizacao=cls.org_b, nome='Prato B', preco=Decimal('30.00'))
        cls.combo_b = Combo.objects.create(organizacao=cls.org_b, nome='Combo B', preco=Decimal('25.00'))
        cls.mesa_a = Mesa.objects.create(organizacao=cls.org_a, numero=1)
        cls.mesa_b = Mesa.objects.create(organizacao=cls.org_b, numero=1)
        cls.comanda_a = Comanda.objects.create(organizacao=cls.org_a, mesa=cls.mesa_a)
        cls.comanda_b = Comanda.objects.create(organizacao=cls.org_b, mesa=cls.mesa_b)
        cls.item_b = ItemComanda.objects.create(comanda=cls.comanda_b, prato=cls.prato_b, quantidade=1)


class ListagensTests(IsolamentoTestBase):
    def test_lista_de_pratos_mostra_so_a_organizacao_do_usuario(self):
        resp = self.client.get(reverse('prato_list'))
        self.assertEqual(list(resp.context['pratos']), [self.prato_a])
        self.assertNotContains(resp, 'Prato B')

    def test_lista_de_combos_mesas_e_comandas_mostram_so_a_organizacao_do_usuario(self):
        self.assertEqual(len(self.client.get(reverse('combo_list')).context['combos']), 0)
        self.assertEqual([m for m, _ in self.client.get(reverse('mesa_list')).context['mesas_com_comanda']], [self.mesa_a])
        self.assertEqual(list(self.client.get(reverse('comanda_list')).context['comandas']), [self.comanda_a])

    def test_usuario_b_ve_apenas_os_dados_dele(self):
        self.client.force_login(self.admin_b)
        resp = self.client.get(reverse('prato_list'))
        self.assertEqual(list(resp.context['pratos']), [self.prato_b])


class IdsDeOutraOrganizacaoTests(IsolamentoTestBase):
    """Trocar o id na URL por um de outra organizacao deve dar 404, nunca mostrar dados alheios."""

    def test_editar_e_excluir_de_outra_organizacao_dao_404(self):
        for nome, objeto in (('prato', self.prato_b), ('combo', self.combo_b), ('mesa', self.mesa_b)):
            for acao in ('update', 'delete'):
                url = reverse(f'{nome}_{acao}', args=[objeto.pk])
                self.assertEqual(self.client.get(url).status_code, 404, url)
                self.assertEqual(self.client.post(url).status_code, 404, url)
        self.assertTrue(Prato.objects.filter(pk=self.prato_b.pk).exists())

    def test_nao_consegue_alterar_prato_de_outra_organizacao(self):
        resp = self.client.post(reverse('prato_update', args=[self.prato_b.pk]), {
            'nome': 'Invadido', 'categoria': 'PRINCIPAL', 'preco': '1.00', 'disponivel': 'on',
        })
        self.assertEqual(resp.status_code, 404)
        self.prato_b.refresh_from_db()
        self.assertEqual(self.prato_b.nome, 'Prato B')

    def test_comanda_de_outra_organizacao_da_404_em_todas_as_acoes(self):
        pk = self.comanda_b.pk
        self.assertEqual(self.client.get(reverse('comanda_detail', args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('fechar_comanda', args=[pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('adicionar_item', args=[pk]), {
            'prato': self.prato_a.pk, 'quantidade': 1}).status_code, 404)
        self.assertEqual(self.client.post(reverse('remover_item', args=[self.item_b.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('abrir_comanda', args=[self.mesa_b.pk])).status_code, 404)
        self.comanda_b.refresh_from_db()
        self.assertEqual(self.comanda_b.status, Comanda.Status.ABERTA)
        self.assertTrue(ItemComanda.objects.filter(pk=self.item_b.pk).exists())


class CriacaoNaOrganizacaoCertaTests(IsolamentoTestBase):
    def test_prato_criado_pelo_usuario_a_fica_na_organizacao_a(self):
        resp = self.client.post(reverse('prato_create'), {
            'nome': 'Novo', 'categoria': 'PRINCIPAL', 'preco': '12.00', 'disponivel': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Prato.objects.get(nome='Novo').organizacao, self.org_a)

    def test_organizacao_enviada_no_formulario_e_ignorada(self):
        self.client.post(reverse('prato_create'), {
            'nome': 'Tentativa', 'categoria': 'PRINCIPAL', 'preco': '12.00', 'disponivel': 'on',
            'organizacao': self.org_b.pk,
        })
        self.assertEqual(Prato.objects.get(nome='Tentativa').organizacao, self.org_a)

    def test_comanda_e_item_nascem_na_organizacao_do_usuario(self):
        self.client.post(reverse('fechar_comanda', args=[self.comanda_a.pk]))  # libera a mesa
        self.client.post(reverse('abrir_comanda', args=[self.mesa_a.pk]))
        comanda = Comanda.objects.filter(mesa=self.mesa_a, status=Comanda.Status.ABERTA).get()
        self.assertEqual(comanda.organizacao, self.org_a)
        self.client.post(reverse('adicionar_item', args=[comanda.pk]), {'prato': self.prato_a.pk, 'quantidade': 2})
        self.assertEqual(comanda.itens.get().organizacao, self.org_a)


class FormulariosTests(IsolamentoTestBase):
    def test_selects_do_formulario_mostram_so_opcoes_da_organizacao(self):
        form = ItemComandaForm(org=self.org_a)
        self.assertEqual(list(form.fields['prato'].queryset), [self.prato_a])
        self.assertEqual(len(form.fields['combo'].queryset), 0)
        self.assertEqual(list(ComboForm(org=self.org_a).fields['pratos'].queryset), [self.prato_a])

    def test_item_com_prato_de_outra_organizacao_e_rejeitado(self):
        resp = self.client.post(reverse('adicionar_item', args=[self.comanda_a.pk]), {
            'prato': self.prato_b.pk, 'quantidade': 1})
        self.assertEqual(resp.status_code, 200)  # formulario invalido, reexibido
        self.assertFalse(self.comanda_a.itens.exists())

    def test_combo_com_prato_de_outra_organizacao_e_rejeitado(self):
        resp = self.client.post(reverse('combo_create'), {
            'nome': 'Combo X', 'preco': '27.00', 'pratos': [self.prato_b.pk], 'disponivel': 'on'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Combo.objects.filter(nome='Combo X').exists())


class UnicidadePorOrganizacaoTests(IsolamentoTestBase):
    def test_mesmo_numero_de_mesa_em_outra_organizacao_e_permitido(self):
        # As duas organizacoes ja tem a "Mesa 1" (setUpTestData). Sem erro de integridade.
        self.assertEqual(Mesa.objects.filter(numero=1).count(), 2)

    def test_numero_duplicado_na_mesma_organizacao_e_rejeitado_com_mensagem(self):
        resp = self.client.post(reverse('mesa_create'), {'numero': 1, 'capacidade': 4})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Ja existe uma mesa com este numero.')
        self.assertEqual(Mesa.objects.filter(organizacao=self.org_a, numero=1).count(), 1)

    def test_editar_a_propria_mesa_sem_mudar_o_numero_funciona(self):
        resp = self.client.post(reverse('mesa_update', args=[self.mesa_a.pk]), {'numero': 1, 'capacidade': 8})
        self.assertEqual(resp.status_code, 302)
        self.mesa_a.refresh_from_db()
        self.assertEqual(self.mesa_a.capacidade, 8)


class AcessoTests(IsolamentoTestBase):
    def test_anonimo_e_enviado_para_o_login(self):
        self.client.logout()
        for nome in ('dashboard', 'prato_list', 'combo_list', 'mesa_list', 'comanda_list'):
            resp = self.client.get(reverse(nome))
            self.assertEqual(resp.status_code, 302, nome)
            self.assertTrue(resp.url.startswith(reverse('login')), nome)

    def test_acoes_que_alteram_dados_nao_aceitam_get(self):
        for url in (reverse('abrir_comanda', args=[self.mesa_a.pk]),
                    reverse('fechar_comanda', args=[self.comanda_a.pk])):
            self.assertEqual(self.client.get(url).status_code, 405)
        self.comanda_a.refresh_from_db()
        self.assertEqual(self.comanda_a.status, Comanda.Status.ABERTA)

    def test_superusuario_sem_perfil_recebe_403_e_nao_erro_500(self):
        super_sem_perfil = User.objects.create_superuser('root', password='x')
        self.client.force_login(super_sem_perfil)
        for nome in ('dashboard', 'prato_list', 'mesa_list'):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403, nome)
        resp = self.client.get(reverse('inicio'))
        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, 'nao esta vinculado a uma organizacao', status_code=403)

    def test_login_leva_ao_dashboard(self):
        self.client.logout()
        usuario = User.objects.create_user('com_senha', password='senha-forte-123')
        Perfil.objects.create(usuario=usuario, organizacao=self.org_a)
        resp = self.client.post(reverse('login'), {'username': 'com_senha', 'password': 'senha-forte-123'})
        self.assertRedirects(resp, reverse('inicio'), fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse('inicio')), reverse('dashboard'))


class CardapioPublicoTests(IsolamentoTestBase):
    def test_publico_mostra_so_itens_disponiveis_da_organizacao_do_slug(self):
        Prato.objects.create(organizacao=self.org_a, nome='Indisponivel', preco=Decimal('5.00'), disponivel=False)
        self.client.logout()  # sem login
        resp = self.client.get(reverse('cardapio_publico', args=[self.org_a.slug]))
        self.assertContains(resp, 'Prato A')
        self.assertNotContains(resp, 'Prato B')
        self.assertNotContains(resp, 'Indisponivel')

    def test_slug_inexistente_da_404(self):
        self.assertEqual(self.client.get(reverse('cardapio_publico', args=['nao-existe'])).status_code, 404)

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .forms import PratoForm
from .models import Combo, Comanda, ItemComanda, Mesa, Prato


class PratoModelTests(TestCase):
    def test_str(self):
        prato = Prato.objects.create(nome='X-Burger', preco=Decimal('25.90'))
        self.assertEqual(str(prato), 'X-Burger')


class ComboModelTests(TestCase):
    def test_str_e_pratos_relacionados(self):
        prato = Prato.objects.create(nome='X-Burger', preco=Decimal('25.90'))
        combo = Combo.objects.create(nome='Combo X', preco=Decimal('40.00'))
        combo.pratos.add(prato)
        self.assertEqual(str(combo), 'Combo X')
        self.assertIn(prato, combo.pratos.all())


class MesaComandaTests(TestCase):
    def test_apenas_uma_comanda_aberta_por_mesa(self):
        mesa = Mesa.objects.create(numero=1, capacidade=4)
        Comanda.objects.create(mesa=mesa)
        with self.assertRaises(Exception):
            Comanda.objects.create(mesa=mesa)

    def test_comanda_aberta_property(self):
        mesa = Mesa.objects.create(numero=1, capacidade=4)
        self.assertIsNone(mesa.comanda_aberta)
        comanda = Comanda.objects.create(mesa=mesa)
        self.assertEqual(mesa.comanda_aberta, comanda)


class ItemComandaTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1, capacidade=4)
        self.comanda = Comanda.objects.create(mesa=self.mesa)
        self.prato = Prato.objects.create(nome='X-Burger', preco=Decimal('25.90'))
        self.combo = Combo.objects.create(nome='Combo X', preco=Decimal('40.00'))

    def test_item_precisa_de_prato_ou_combo(self):
        item = ItemComanda(comanda=self.comanda, quantidade=1)
        with self.assertRaises(ValidationError):
            item.clean()

    def test_item_nao_pode_ter_prato_e_combo(self):
        item = ItemComanda(comanda=self.comanda, prato=self.prato, combo=self.combo, quantidade=1)
        with self.assertRaises(ValidationError):
            item.clean()

    def test_preco_unitario_e_definido_automaticamente(self):
        item = ItemComanda.objects.create(comanda=self.comanda, prato=self.prato, quantidade=3)
        self.assertEqual(item.preco_unitario, self.prato.preco)
        self.assertEqual(item.subtotal, self.prato.preco * 3)


class ComandaFechamentoTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1, capacidade=4)
        self.comanda = Comanda.objects.create(mesa=self.mesa)
        self.prato = Prato.objects.create(nome='X-Burger', preco=Decimal('25.90'))

    def test_fechar_calcula_total_e_muda_status(self):
        ItemComanda.objects.create(comanda=self.comanda, prato=self.prato, quantidade=2)
        self.comanda.fechar()
        self.assertEqual(self.comanda.status, Comanda.Status.FECHADA)
        self.assertEqual(self.comanda.total, Decimal('51.80'))
        self.assertIsNotNone(self.comanda.fechada_em)

    def test_fechar_comanda_ja_fechada_gera_erro(self):
        self.comanda.fechar()
        with self.assertRaises(ValidationError):
            self.comanda.fechar()


class PratoBuscaFiltroTests(TestCase):
    def setUp(self):
        self.burger = Prato.objects.create(
            nome='X-Burger', categoria=Prato.Categoria.PRINCIPAL, preco=Decimal('25.90'))
        self.cheddar = Prato.objects.create(
            nome='Burger Cheddar', categoria=Prato.Categoria.PRINCIPAL, preco=Decimal('29.90'))
        self.suco = Prato.objects.create(
            nome='Suco Natural', categoria=Prato.Categoria.BEBIDA, preco=Decimal('9.50'))

    def listar(self, **params):
        return self.client.get(reverse('prato_list'), params)

    def test_sem_filtros_lista_todos(self):
        resp = self.listar()
        self.assertEqual(len(resp.context['pratos']), 3)

    def test_busca_por_nome_nao_diferencia_maiusculas(self):
        resp = self.listar(q='BURGER')
        self.assertCountEqual(resp.context['pratos'], [self.burger, self.cheddar])

    def test_filtro_por_categoria(self):
        resp = self.listar(categoria='BEBIDA')
        self.assertCountEqual(resp.context['pratos'], [self.suco])

    def test_busca_e_categoria_combinadas(self):
        resp = self.listar(q='cheddar', categoria='PRINCIPAL')
        self.assertCountEqual(resp.context['pratos'], [self.cheddar])
        resp = self.listar(q='burger', categoria='BEBIDA')
        self.assertEqual(len(resp.context['pratos']), 0)

    def test_categoria_invalida_e_ignorada(self):
        resp = self.listar(categoria='INEXISTENTE')
        self.assertEqual(len(resp.context['pratos']), 3)

    def test_sem_resultado_mostra_mensagem(self):
        resp = self.listar(q='lasanha')
        self.assertContains(resp, 'Nenhum prato encontrado para os filtros informados.')

    def test_campos_mantem_valores_da_pesquisa(self):
        resp = self.listar(q='burger', categoria='PRINCIPAL')
        self.assertContains(resp, 'name="q" value="burger"')
        self.assertContains(resp, '<option value="PRINCIPAL" selected>')


class PratoFormPrecoTests(TestCase):
    def dados(self, preco):
        return {'nome': 'Teste', 'descricao': '', 'categoria': 'PRINCIPAL', 'preco': preco, 'disponivel': 'on'}

    def test_preco_positivo_e_aceito(self):
        self.assertTrue(PratoForm(data=self.dados('0.01')).is_valid())

    def test_preco_zero_ou_negativo_e_rejeitado(self):
        for preco in ('0', '0.00', '-5.00'):
            form = PratoForm(data=self.dados(preco))
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors['preco'], ['O preco do prato deve ser maior que zero.'])

    def test_mensagem_aparece_no_template_e_prato_nao_e_salvo(self):
        resp = self.client.post(reverse('prato_create'), self.dados('0'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'O preco do prato deve ser maior que zero.')
        self.assertFalse(Prato.objects.filter(nome='Teste').exists())

    def test_edicao_tambem_valida_o_preco(self):
        prato = Prato.objects.create(nome='Teste', preco=Decimal('10.00'))
        resp = self.client.post(reverse('prato_update', args=[prato.pk]), self.dados('-1'))
        self.assertContains(resp, 'O preco do prato deve ser maior que zero.')
        prato.refresh_from_db()
        self.assertEqual(prato.preco, Decimal('10.00'))


class ViewsFluxoTests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=1, capacidade=4)
        self.prato = Prato.objects.create(nome='X-Burger', preco=Decimal('25.90'))

    def test_prato_crud_via_views(self):
        resp = self.client.post(reverse('prato_create'), {
            'nome': 'Batata Frita', 'descricao': '', 'categoria': 'ACOMPANHAMENTO', 'preco': '18.50', 'disponivel': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        prato = Prato.objects.get(nome='Batata Frita')

        resp = self.client.post(reverse('prato_update', args=[prato.pk]), {
            'nome': 'Batata Frita Grande', 'descricao': '', 'categoria': 'ACOMPANHAMENTO', 'preco': '22.00', 'disponivel': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        prato.refresh_from_db()
        self.assertEqual(prato.nome, 'Batata Frita Grande')

        resp = self.client.post(reverse('prato_delete', args=[prato.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Prato.objects.filter(pk=prato.pk).exists())

    def test_prato_em_uso_nao_pode_ser_excluido(self):
        comanda = Comanda.objects.create(mesa=self.mesa)
        ItemComanda.objects.create(comanda=comanda, prato=self.prato, quantidade=1)
        resp = self.client.post(reverse('prato_delete', args=[self.prato.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Prato.objects.filter(pk=self.prato.pk).exists())

    def test_abrir_comanda_reaproveita_comanda_aberta(self):
        resp1 = self.client.get(reverse('abrir_comanda', args=[self.mesa.pk]))
        resp2 = self.client.get(reverse('abrir_comanda', args=[self.mesa.pk]))
        self.assertEqual(resp1.url, resp2.url)
        self.assertEqual(Comanda.objects.filter(mesa=self.mesa).count(), 1)

    def test_fluxo_completo_lancar_item_e_fechar_conta(self):
        resp = self.client.get(reverse('abrir_comanda', args=[self.mesa.pk]))
        comanda = Comanda.objects.get(mesa=self.mesa, status=Comanda.Status.ABERTA)

        resp = self.client.post(reverse('adicionar_item', args=[comanda.pk]), {
            'prato': self.prato.pk, 'combo': '', 'quantidade': '2',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(comanda.itens.count(), 1)

        resp = self.client.get(reverse('fechar_comanda', args=[comanda.pk]))
        self.assertEqual(resp.status_code, 302)
        comanda.refresh_from_db()
        self.assertEqual(comanda.status, Comanda.Status.FECHADA)
        self.assertEqual(comanda.total, Decimal('51.80'))

        resp = self.client.post(reverse('adicionar_item', args=[comanda.pk]), {
            'prato': self.prato.pk, 'combo': '', 'quantidade': '1',
        })
        self.assertEqual(comanda.itens.count(), 1)

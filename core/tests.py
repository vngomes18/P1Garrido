from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.test import TestCase

from cardapio.models import Prato

from .models import Organizacao, Perfil


class OrganizacaoTests(TestCase):
    def test_slug_e_gerado_a_partir_do_nome(self):
        org = Organizacao.objects.create(nome='Burger House')
        self.assertEqual(org.slug, 'burger-house')
        self.assertEqual(str(org), 'Burger House')

    def test_organizacao_com_dados_nao_pode_ser_apagada(self):
        org = Organizacao.objects.create(nome='Com dados')
        Prato.objects.create(organizacao=org, nome='X', preco=10)
        with self.assertRaises(ProtectedError):
            org.delete()


class PerfilTests(TestCase):
    def setUp(self):
        self.org = Organizacao.objects.create(nome='Org')
        self.usuario = User.objects.create_user('maria')

    def test_papel_padrao_e_operador(self):
        perfil = Perfil.objects.create(usuario=self.usuario, organizacao=self.org)
        self.assertEqual(perfil.papel, Perfil.OPERADOR)
        self.assertFalse(perfil.eh_admin)

    def test_administrador(self):
        perfil = Perfil.objects.create(usuario=self.usuario, organizacao=self.org, papel=Perfil.ADMIN)
        self.assertTrue(perfil.eh_admin)

    def test_usuario_acessa_o_perfil_e_a_organizacao(self):
        Perfil.objects.create(usuario=self.usuario, organizacao=self.org)
        self.assertEqual(self.usuario.perfil.organizacao, self.org)

    def test_um_usuario_so_pode_ter_um_perfil(self):
        Perfil.objects.create(usuario=self.usuario, organizacao=self.org)
        outra = Organizacao.objects.create(nome='Outra')
        with self.assertRaises(Exception):
            Perfil.objects.create(usuario=self.usuario, organizacao=outra)

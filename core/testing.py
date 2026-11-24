"""Apoio aos testes: duas organizacoes, cada uma com administrador e operador.

Para provar o isolamento (Aula 14) e preciso SEMPRE ter dois "inquilinos".
"""
from django.contrib.auth.models import User

from .models import Organizacao, Perfil

SENHA = 'senha1234'


def criar_usuario(username, org, papel):
    # Sem senha (hash lento): os testes entram com client.force_login().
    usuario = User.objects.create_user(username=username)
    Perfil.objects.create(usuario=usuario, organizacao=org, papel=papel)
    return usuario


class DuasOrganizacoesMixin:
    """Misture antes de TestCase. Por padrao o cliente entra logado como administrador da Org A."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.org_a = Organizacao.objects.create(nome='Org A')
        cls.org_b = Organizacao.objects.create(nome='Org B')
        cls.admin_a = criar_usuario('admin_a', cls.org_a, Perfil.ADMIN)
        cls.operador_a = criar_usuario('operador_a', cls.org_a, Perfil.OPERADOR)
        cls.admin_b = criar_usuario('admin_b', cls.org_b, Perfil.ADMIN)
        cls.operador_b = criar_usuario('operador_b', cls.org_b, Perfil.OPERADOR)

    def setUp(self):
        super().setUp()
        self.client.force_login(self.admin_a)

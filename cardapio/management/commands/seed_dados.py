import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from cardapio.models import Combo, Comanda, ItemComanda, Mesa, Prato
from core.models import Organizacao, Perfil

SENHA_DEMO = 'senha1234'  # SOMENTE para desenvolvimento/demonstracao

ORGANIZACOES = {
    'Burger House': {
        'usuarios': {'ana': Perfil.ADMIN, 'ana.op': Perfil.OPERADOR},
        'pratos': [
            ('X-Burger', Prato.Categoria.PRINCIPAL, 'Pao, hamburguer, queijo e salada.', '25.90'),
            ('Batata Frita', Prato.Categoria.ACOMPANHAMENTO, 'Porcao de batata frita crocante.', '18.50'),
            ('Refrigerante', Prato.Categoria.BEBIDA, 'Lata 350ml.', '7.00'),
            ('Salada Caesar', Prato.Categoria.ENTRADA, 'Alface, frango grelhado, croutons e molho caesar.', '29.90'),
            ('Suco Natural', Prato.Categoria.BEBIDA, 'Copo 400ml, sabores variados.', '9.50'),
            ('Brownie', Prato.Categoria.SOBREMESA, 'Brownie com sorvete.', '16.00'),
        ],
        'combos': [('Combo X-Burger', 'X-Burger + Batata Frita + Refrigerante.', '45.00',
                    ['X-Burger', 'Batata Frita', 'Refrigerante'])],
    },
    'Cantina Bella': {
        'usuarios': {'bruno': Perfil.ADMIN, 'bruno.op': Perfil.OPERADOR},
        'pratos': [
            ('Lasanha', Prato.Categoria.PRINCIPAL, 'Lasanha a bolonhesa.', '38.00'),
            ('Salada Caprese', Prato.Categoria.ENTRADA, 'Tomate, mussarela de bufala e manjericao.', '24.00'),
            ('Pao de Alho', Prato.Categoria.ACOMPANHAMENTO, 'Porcao com 4 unidades.', '14.00'),
            ('Suco de Uva', Prato.Categoria.BEBIDA, 'Copo 400ml.', '9.50'),
            ('Tiramisu', Prato.Categoria.SOBREMESA, 'Fatia individual.', '19.00'),
        ],
        'combos': [('Combo Lasanha', 'Lasanha + Suco de Uva.', '41.00', ['Lasanha', 'Suco de Uva'])],
    },
}


class Command(BaseCommand):
    help = (
        'Popula o banco com 2 organizacoes, usuarios (admin e operador), mesas, pratos, combos '
        'e um historico de comandas fechadas para o dashboard. Apenas para desenvolvimento.'
    )

    def handle(self, *args, **options):
        for nome, dados in ORGANIZACOES.items():
            org, _ = Organizacao.objects.get_or_create(nome=nome)
            self.stdout.write(self.style.SUCCESS(f'Organizacao: {org}'))

            for username, papel in dados['usuarios'].items():
                usuario, criado = User.objects.get_or_create(username=username)
                if criado:
                    usuario.set_password(SENHA_DEMO)
                    usuario.save()
                Perfil.objects.get_or_create(usuario=usuario, defaults={'organizacao': org, 'papel': papel})
                self.stdout.write(f'  usuario {username} ({papel})')

            pratos = {}
            for nome_prato, categoria, descricao, preco in dados['pratos']:
                prato, _ = Prato.objects.get_or_create(
                    organizacao=org, nome=nome_prato,
                    defaults={'categoria': categoria, 'descricao': descricao, 'preco': preco},
                )
                pratos[nome_prato] = prato

            combos = []
            for nome_combo, descricao, preco, itens in dados['combos']:
                combo, criado = Combo.objects.get_or_create(
                    organizacao=org, nome=nome_combo, defaults={'descricao': descricao, 'preco': preco},
                )
                if criado:
                    combo.pratos.set([pratos[i] for i in itens])
                combos.append(combo)

            mesas = [
                Mesa.objects.get_or_create(organizacao=org, numero=n, defaults={'capacidade': 4})[0]
                for n in range(1, 6)
            ]

            if not Comanda.objects.filter(organizacao=org).exists():
                self._historico(org, mesas, list(pratos.values()), combos)

        self.stdout.write(self.style.SUCCESS(f'Seed concluido. Senha de todos os usuarios de demonstracao: {SENHA_DEMO}'))

    def _historico(self, org, mesas, pratos, combos):
        """Comandas fechadas nos ultimos 3 meses (datas ajustadas por update: auto_now_add ignora o valor)."""
        sorteio = random.Random(org.pk)  # reproduzivel
        agora = timezone.now()
        for dias_atras in range(5, 90, 3):
            quando = agora - timedelta(days=dias_atras)
            comanda = Comanda.objects.create(mesa=sorteio.choice(mesas), organizacao=org)
            for _ in range(sorteio.randint(1, 4)):
                produto = sorteio.choice(pratos + combos)
                chave = 'prato' if isinstance(produto, Prato) else 'combo'
                ItemComanda.objects.create(
                    comanda=comanda, organizacao=org, quantidade=sorteio.randint(1, 3), **{chave: produto},
                )
            comanda.fechar()
            Comanda.objects.filter(pk=comanda.pk).update(aberta_em=quando, fechada_em=quando + timedelta(minutes=50))

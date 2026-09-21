from django.core.management.base import BaseCommand

from cardapio.models import Combo, Mesa, Prato


class Command(BaseCommand):
    help = 'Popula o banco com mesas, pratos e combos de exemplo para desenvolvimento.'

    def handle(self, *args, **options):
        pratos_dados = [
            {'nome': 'X-Burger', 'descricao': 'Pao, hamburguer, queijo e salada.', 'preco': '25.90'},
            {'nome': 'Batata Frita', 'descricao': 'Porcao de batata frita crocante.', 'preco': '18.50'},
            {'nome': 'Refrigerante', 'descricao': 'Lata 350ml.', 'preco': '7.00'},
            {'nome': 'Salada Caesar', 'descricao': 'Alface, frango grelhado, croutons e molho caesar.', 'preco': '29.90'},
            {'nome': 'Suco Natural', 'descricao': 'Copo 400ml, sabores variados.', 'preco': '9.50'},
        ]

        pratos = {}
        for dados in pratos_dados:
            prato, criado = Prato.objects.get_or_create(nome=dados['nome'], defaults=dados)
            pratos[prato.nome] = prato
            self.stdout.write(self.style.SUCCESS(f'Prato {"criado" if criado else "ja existia"}: {prato.nome}'))

        combo, criado = Combo.objects.get_or_create(
            nome='Combo X-Burger',
            defaults={
                'descricao': 'X-Burger + Batata Frita + Refrigerante.',
                'preco': '45.00',
            },
        )
        if criado:
            combo.pratos.set([pratos['X-Burger'], pratos['Batata Frita'], pratos['Refrigerante']])
        self.stdout.write(self.style.SUCCESS(f'Combo {"criado" if criado else "ja existia"}: {combo.nome}'))

        for numero in range(1, 6):
            mesa, criado = Mesa.objects.get_or_create(numero=numero, defaults={'capacidade': 4})
            self.stdout.write(self.style.SUCCESS(f'Mesa {"criada" if criado else "ja existia"}: {mesa}'))

        self.stdout.write(self.style.SUCCESS('Seed concluido.'))

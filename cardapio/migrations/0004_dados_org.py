"""Etapa 2 de 3 (Aula 14): migracao de dados.

Todo registro criado na P1 passa a pertencer a "Organizacao padrao".
Usa apps.get_model (e nao import direto) para enxergar os models como eram
neste ponto do historico.
"""
from django.db import migrations

MODELOS = ['Prato', 'Combo', 'Mesa', 'Comanda', 'ItemComanda']


def org_padrao(apps, schema_editor):
    Organizacao = apps.get_model('core', 'Organizacao')
    org, _ = Organizacao.objects.get_or_create(
        slug='organizacao-padrao', defaults={'nome': 'Organizacao padrao'},
    )
    for nome in MODELOS:
        Modelo = apps.get_model('cardapio', nome)
        Modelo.objects.filter(organizacao__isnull=True).update(organizacao=org)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('cardapio', '0003_organizacao_nula'),
    ]

    operations = [
        migrations.RunPython(org_padrao, migrations.RunPython.noop),
    ]

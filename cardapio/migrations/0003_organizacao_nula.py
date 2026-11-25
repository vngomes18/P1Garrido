"""Etapa 1 de 3 (Aula 14): adiciona a FK da organizacao PERMITINDO nulo.

Os registros da P1 ja existem e ainda nao tem organizacao; por isso a coluna
nasce opcional. A etapa 2 (0004) preenche e a etapa 3 (0005) torna obrigatoria.
"""
import django.db.models.deletion
from django.db import migrations, models

MODELOS = ['prato', 'combo', 'mesa', 'comanda', 'itemcomanda']


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('cardapio', '0002_prato_categoria'),
    ]

    operations = [
        migrations.AddField(
            model_name=modelo,
            name='organizacao',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to='core.organizacao',
            ),
        )
        for modelo in MODELOS
    ]

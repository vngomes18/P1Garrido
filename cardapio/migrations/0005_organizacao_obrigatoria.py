"""Etapa 3 de 3 (Aula 14): FK obrigatoria, unicidade por organizacao e validators de preco."""
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import cardapio.validators

MODELOS = ['prato', 'combo', 'mesa', 'comanda', 'itemcomanda']


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('cardapio', '0004_dados_org'),
    ]

    operations = [
        migrations.AlterField(
            model_name=modelo,
            name='organizacao',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to='core.organizacao',
            ),
        )
        for modelo in MODELOS
    ] + [
        # unique=True global vira unicidade POR organizacao.
        migrations.AlterField(
            model_name='mesa',
            name='numero',
            field=models.PositiveIntegerField(),
        ),
        migrations.AddConstraint(
            model_name='mesa',
            constraint=models.UniqueConstraint(
                fields=('organizacao', 'numero'), name='mesa_numero_unico_por_org',
            ),
        ),
        migrations.AlterField(
            model_name='prato',
            name='preco',
            field=models.DecimalField(
                decimal_places=2, max_digits=8,
                validators=[cardapio.validators.preco_prato_positivo],
            ),
        ),
        migrations.AlterField(
            model_name='combo',
            name='preco',
            field=models.DecimalField(
                decimal_places=2, max_digits=8,
                validators=[cardapio.validators.preco_combo_positivo],
            ),
        ),
        migrations.AlterField(
            model_name='itemcomanda',
            name='quantidade',
            field=models.PositiveIntegerField(
                default=1, validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
    ]

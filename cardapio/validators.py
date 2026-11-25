"""Regras de negocio do P1, em UM lugar so, reaproveitadas por formularios, Admin e API.

(Aula 13: "mantenha um lugar principal para cada regra e reaproveite".)
"""
from decimal import ROUND_DOWN, ROUND_UP, Decimal

from django.core.exceptions import ValidationError

DESCONTO_MINIMO_COMBO = Decimal('0.10')
DESCONTO_MAXIMO_COMBO = Decimal('0.15')
CENTAVO = Decimal('0.01')


def preco_prato_positivo(valor):
    # Preco zero ou negativo zeraria/abateria o total da comanda no fechamento.
    if valor is not None and valor <= 0:
        raise ValidationError('O preco do prato deve ser maior que zero.', code='preco_invalido')


def preco_combo_positivo(valor):
    if valor is not None and valor <= 0:
        raise ValidationError('O preco do combo deve ser maior que zero.', code='preco_invalido')


def validar_desconto_combo(preco, pratos):
    """O combo precisa sair de 10% a 15% mais barato que a soma dos pratos avulsos."""
    # Preco ausente ou <= 0 ja e recusado por preco_combo_positivo: nao duplica a mensagem.
    if preco is None or preco <= 0 or not pratos:
        return
    soma = sum((prato.preco for prato in pratos), Decimal('0.00'))
    preco_maximo = soma * (1 - DESCONTO_MINIMO_COMBO)
    preco_minimo = soma * (1 - DESCONTO_MAXIMO_COMBO)
    if not preco_minimo <= preco <= preco_maximo:
        raise ValidationError(
            f'O combo deve ter de 10% a 15% de desconto sobre a soma dos pratos '
            f'(R$ {soma.quantize(CENTAVO)}). Informe um preco entre '
            f'R$ {preco_minimo.quantize(CENTAVO, rounding=ROUND_UP)} e '
            f'R$ {preco_maximo.quantize(CENTAVO, rounding=ROUND_DOWN)}.',
            code='desconto_invalido',
        )

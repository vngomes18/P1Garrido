"""Serializers da API (Aula 13). Sempre com `fields` explicitos: nada de "__all__".

A organizacao NUNCA aparece como campo: ela vem do usuario logado (view) e os
ids de relacionamentos so sao aceitos se forem da propria organizacao.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Combo, Comanda, ItemComanda, Mesa, Prato
from .validators import validar_desconto_combo


class OrgPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """Aceita apenas ids de registros da organizacao do usuario logado (evita vazamento por id)."""

    def get_queryset(self):
        queryset = super().get_queryset()
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated or not hasattr(request.user, 'perfil'):
            return queryset.none()
        return queryset.filter(organizacao=request.user.perfil.organizacao)


class PratoSerializer(serializers.ModelSerializer):
    # A regra "preco > 0" vem do validator do model (cardapio/validators.py).
    class Meta:
        model = Prato
        fields = ['id', 'nome', 'descricao', 'categoria', 'preco', 'disponivel']


class ComboSerializer(serializers.ModelSerializer):
    pratos = OrgPrimaryKeyRelatedField(many=True, queryset=Prato.objects.all(), allow_empty=False)

    class Meta:
        model = Combo
        fields = ['id', 'nome', 'descricao', 'preco', 'pratos', 'disponivel']

    def validate(self, data):
        # Regra de varios campos (preco x soma dos pratos): a mesma do formulario.
        preco = data.get('preco', getattr(self.instance, 'preco', None))
        pratos = data.get('pratos')
        if pratos is None and self.instance is not None:
            pratos = list(self.instance.pratos.all())
        try:
            validar_desconto_combo(preco, pratos)
        except DjangoValidationError as erro:
            raise serializers.ValidationError({'preco': erro.messages})
        return data


class MesaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mesa
        fields = ['id', 'numero', 'capacidade']

    def validate_numero(self, value):
        # Unicidade e POR organizacao; como a organizacao nao e um campo, validamos aqui.
        org = self.context['request'].user.perfil.organizacao
        duplicadas = Mesa.objects.filter(organizacao=org, numero=value)
        if self.instance is not None:
            duplicadas = duplicadas.exclude(pk=self.instance.pk)
        if duplicadas.exists():
            raise serializers.ValidationError('Ja existe uma mesa com este numero.')
        return value


class ItemComandaSerializer(serializers.ModelSerializer):
    prato = OrgPrimaryKeyRelatedField(queryset=Prato.objects.filter(disponivel=True), required=False, allow_null=True)
    combo = OrgPrimaryKeyRelatedField(queryset=Combo.objects.filter(disponivel=True), required=False, allow_null=True)
    descricao = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=11, decimal_places=2, read_only=True)

    class Meta:
        model = ItemComanda
        fields = ['id', 'prato', 'combo', 'descricao', 'quantidade', 'preco_unitario', 'subtotal']
        read_only_fields = ['preco_unitario']

    def get_descricao(self, obj):
        return str(obj.prato or obj.combo)

    def validate(self, data):
        if bool(data.get('prato')) == bool(data.get('combo')):
            raise serializers.ValidationError('Selecione um prato ou um combo, nao ambos nem nenhum.')
        return data


class ComandaSerializer(serializers.ModelSerializer):
    mesa = OrgPrimaryKeyRelatedField(queryset=Mesa.objects.all())
    mesa_numero = serializers.IntegerField(source='mesa.numero', read_only=True)
    itens = ItemComandaSerializer(many=True, read_only=True)

    class Meta:
        model = Comanda
        fields = ['id', 'mesa', 'mesa_numero', 'status', 'aberta_em', 'fechada_em', 'total', 'itens']
        read_only_fields = ['status', 'aberta_em', 'fechada_em', 'total']

    def validate_mesa(self, mesa):
        if mesa.comandas.filter(status=Comanda.Status.ABERTA).exists():
            raise serializers.ValidationError('Esta mesa ja possui uma comanda aberta.')
        return mesa

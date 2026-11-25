"""Views da API (Aula 13): generics do DRF. Cada recurso tem 2 classes (lista/cria e detalhe)."""
from decimal import Decimal

from django.db.models import Prefetch
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import AdminEscreveOperadorLe, TemPerfil

from . import dashboard as metricas
from .models import Combo, Comanda, ItemComanda, Mesa, Prato
from .serializers import (
    ComandaSerializer,
    ComboSerializer,
    ItemComandaSerializer,
    MesaSerializer,
    PratoSerializer,
)


def org_da_requisicao(request):
    return request.user.perfil.organizacao


class OrgApiMixin:
    """Toda consulta parte da organizacao do usuario; todo registro novo nasce nela."""

    def get_queryset(self):
        return super().get_queryset().filter(organizacao=org_da_requisicao(self.request))

    def perform_create(self, serializer):
        serializer.save(organizacao=org_da_requisicao(self.request))


class ProtegidoMixin:
    """Registro em uso (ex.: prato dentro de uma comanda) nao pode ser apagado: 409, nao erro 500."""

    mensagem_protegido = 'Nao e possivel excluir: o registro esta em uso.'

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response({'detail': self.mensagem_protegido}, status=status.HTTP_409_CONFLICT)


# ---- Pratos ----

class PratoListCreate(OrgApiMixin, generics.ListCreateAPIView):
    queryset = Prato.objects.all()
    serializer_class = PratoSerializer
    permission_classes = [AdminEscreveOperadorLe]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('q', '').strip()
        categoria = self.request.query_params.get('categoria', '')
        if q:
            qs = qs.filter(nome__icontains=q)
        if categoria in Prato.Categoria.values:
            qs = qs.filter(categoria=categoria)
        return qs


class PratoDetail(OrgApiMixin, ProtegidoMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Prato.objects.all()
    serializer_class = PratoSerializer
    permission_classes = [AdminEscreveOperadorLe]
    mensagem_protegido = 'Nao e possivel excluir: prato esta em uso em uma ou mais comandas.'


# ---- Combos ----

class ComboListCreate(OrgApiMixin, generics.ListCreateAPIView):
    queryset = Combo.objects.prefetch_related('pratos')
    serializer_class = ComboSerializer
    permission_classes = [AdminEscreveOperadorLe]


class ComboDetail(OrgApiMixin, ProtegidoMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Combo.objects.prefetch_related('pratos')
    serializer_class = ComboSerializer
    permission_classes = [AdminEscreveOperadorLe]
    mensagem_protegido = 'Nao e possivel excluir: combo esta em uso em uma ou mais comandas.'


# ---- Mesas ----

class MesaListCreate(OrgApiMixin, generics.ListCreateAPIView):
    queryset = Mesa.objects.all()
    serializer_class = MesaSerializer
    permission_classes = [AdminEscreveOperadorLe]


class MesaDetail(OrgApiMixin, ProtegidoMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Mesa.objects.all()
    serializer_class = MesaSerializer
    permission_classes = [AdminEscreveOperadorLe]
    mensagem_protegido = 'Nao e possivel excluir: mesa possui comandas vinculadas.'


# ---- Comandas (qualquer perfil opera: abrir, lancar itens, fechar) ----

ITENS = Prefetch('itens', queryset=ItemComanda.objects.select_related('prato', 'combo'))


class ComandaListCreate(OrgApiMixin, generics.ListCreateAPIView):
    queryset = Comanda.objects.select_related('mesa').prefetch_related(ITENS)
    serializer_class = ComandaSerializer
    permission_classes = [TemPerfil]

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status', '')
        if status_param in Comanda.Status.values:
            qs = qs.filter(status=status_param)
        return qs


class ComandaDetail(OrgApiMixin, generics.RetrieveAPIView):
    queryset = Comanda.objects.select_related('mesa').prefetch_related(ITENS)
    serializer_class = ComandaSerializer
    permission_classes = [TemPerfil]


class ComandaFechar(APIView):
    permission_classes = [TemPerfil]

    def post(self, request, pk):
        comanda = get_object_or_404(Comanda, pk=pk, organizacao=org_da_requisicao(request))
        if comanda.status != Comanda.Status.ABERTA:
            raise serializers.ValidationError({'detail': 'Esta comanda ja esta fechada.'})
        comanda.fechar()
        comanda = Comanda.objects.select_related('mesa').prefetch_related(ITENS).get(pk=comanda.pk)
        return Response(ComandaSerializer(comanda, context={'request': request}).data)


class ItemCreate(generics.CreateAPIView):
    """POST /api/comandas/<id>/itens/ - lanca um prato ou combo na comanda aberta."""

    serializer_class = ItemComandaSerializer
    permission_classes = [TemPerfil]

    def create(self, request, *args, **kwargs):
        # 404 primeiro: comanda de outra organizacao "nao existe".
        self.comanda = get_object_or_404(Comanda, pk=kwargs['comanda_id'], organizacao=org_da_requisicao(request))
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        if self.comanda.status != Comanda.Status.ABERTA:
            raise serializers.ValidationError({'detail': 'Esta comanda ja esta fechada.'})
        serializer.save(comanda=self.comanda, organizacao=self.comanda.organizacao)


class ItemDestroy(generics.DestroyAPIView):
    serializer_class = ItemComandaSerializer
    permission_classes = [TemPerfil]

    def get_queryset(self):
        return ItemComanda.objects.filter(organizacao=org_da_requisicao(self.request)).select_related('comanda')

    def perform_destroy(self, instance):
        if instance.comanda.status != Comanda.Status.ABERTA:
            raise serializers.ValidationError({'detail': 'Esta comanda ja esta fechada.'})
        instance.delete()


# ---- Dashboard em JSON (mesmas funcoes da tela) ----

class DashboardApi(APIView):
    permission_classes = [TemPerfil]

    def get(self, request):
        perfil = request.user.perfil
        dados = metricas.resumo(perfil.organizacao, request.query_params, incluir_series=perfil.eh_admin)
        # Dinheiro como texto com 2 casas ("78.00"), igual aos demais endpoints (o JSON puro usaria float).
        dados['kpis'] = {k: f'{v:.2f}' if isinstance(v, Decimal) else v for k, v in dados['kpis'].items()}
        for linha in dados.get('por_mes', []):
            linha['total'] = f"{linha['total']:.2f}"
        return Response(dados)

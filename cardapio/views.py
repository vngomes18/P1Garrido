import csv

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.models import Organizacao
from core.permissions import (
    PerfilRequeridoMixin,
    SomenteAdminMixin,
    org_atual,
    papel_requerido,
    perfil_do_usuario,
    perfil_requerido,
)

from . import dashboard as metricas
from .forms import ComboForm, ItemComandaForm, MesaForm, PeriodoForm, PratoForm
from .models import Combo, Comanda, ItemComanda, Mesa, Prato


# ---- Mixins de isolamento (Aula 14): toda consulta parte da organizacao do usuario ----

class FiltraPorOrganizacaoMixin:
    """Lista, detalha, edita e exclui SOMENTE registros da organizacao do usuario logado.

    Registro de outra organizacao gera 404, como se nao existisse.
    """

    def get_queryset(self):
        return super().get_queryset().filter(organizacao=org_atual(self.request))


class SalvaNaOrganizacaoMixin:
    """Formularios recebem `org` (filtra selects) e o registro e gravado na organizacao do usuario.

    A organizacao NAO esta no formulario: se estivesse, o usuario poderia escolher qualquer uma.
    """

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['org'] = org_atual(self.request)
        return kwargs

    def form_valid(self, form):
        objeto = form.save(commit=False)
        objeto.organizacao = org_atual(self.request)
        objeto.save()
        form.save_m2m()
        self.object = objeto
        return redirect(self.get_success_url())


class ProtectedDeleteMixin:
    protected_message = 'Nao e possivel excluir: este registro esta vinculado a outros dados.'

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, self.protected_message)
            return redirect(self.success_url)


# ---- Entrada, cardapio publico ----

def inicio(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if perfil_do_usuario(request.user) is None:
        return render(request, '403.html', {
            'exception': 'Seu usuario ainda nao esta vinculado a uma organizacao.',
        }, status=403)
    return redirect('dashboard')


def cardapio_publico(request, slug):
    """Pagina publica (QR code na mesa): mostra apenas itens disponiveis da organizacao do slug."""
    org = get_object_or_404(Organizacao, slug=slug)
    pratos = Prato.objects.filter(organizacao=org, disponivel=True)
    combos = Combo.objects.filter(organizacao=org, disponivel=True).prefetch_related('pratos')
    return render(request, 'cardapio/cardapio_publico.html', {
        'organizacao': org, 'pratos': pratos, 'combos': combos,
    })


# ---- Prato CRUD (leitura: qualquer perfil; escrita: administrador) ----

class PratoListView(PerfilRequeridoMixin, FiltraPorOrganizacaoMixin, ListView):
    model = Prato
    template_name = 'cardapio/prato_list.html'
    context_object_name = 'pratos'

    def get_queryset(self):
        q = self.request.GET.get('q', '').strip()
        categoria = self.request.GET.get('categoria', '')

        # Busca por nome e filtro por categoria combinados em uma unica consulta com Q().
        filtros = Q()
        if q:
            filtros &= Q(nome__icontains=q)
        if categoria in Prato.Categoria.values:
            filtros &= Q(categoria=categoria)
        return super().get_queryset().filter(filtros)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Prato.Categoria.choices
        context['filtrando'] = bool(self.request.GET.get('q', '').strip() or self.request.GET.get('categoria'))
        return context


class PratoCreateView(SomenteAdminMixin, SalvaNaOrganizacaoMixin, CreateView):
    model = Prato
    form_class = PratoForm
    template_name = 'cardapio/prato_form.html'
    success_url = reverse_lazy('prato_list')


class PratoUpdateView(SomenteAdminMixin, FiltraPorOrganizacaoMixin, SalvaNaOrganizacaoMixin, UpdateView):
    model = Prato
    form_class = PratoForm
    template_name = 'cardapio/prato_form.html'
    success_url = reverse_lazy('prato_list')


class PratoDeleteView(SomenteAdminMixin, FiltraPorOrganizacaoMixin, ProtectedDeleteMixin, DeleteView):
    model = Prato
    template_name = 'cardapio/prato_confirm_delete.html'
    success_url = reverse_lazy('prato_list')
    protected_message = 'Nao e possivel excluir: prato esta em uso em uma ou mais comandas.'


# ---- Combo CRUD ----

class ComboListView(PerfilRequeridoMixin, FiltraPorOrganizacaoMixin, ListView):
    model = Combo
    template_name = 'cardapio/combo_list.html'
    context_object_name = 'combos'

    def get_queryset(self):
        # prefetch_related evita uma consulta extra por combo ao listar os pratos (N+1).
        return super().get_queryset().prefetch_related('pratos')


class ComboCreateView(SomenteAdminMixin, SalvaNaOrganizacaoMixin, CreateView):
    model = Combo
    form_class = ComboForm
    template_name = 'cardapio/combo_form.html'
    success_url = reverse_lazy('combo_list')


class ComboUpdateView(SomenteAdminMixin, FiltraPorOrganizacaoMixin, SalvaNaOrganizacaoMixin, UpdateView):
    model = Combo
    form_class = ComboForm
    template_name = 'cardapio/combo_form.html'
    success_url = reverse_lazy('combo_list')


class ComboDeleteView(SomenteAdminMixin, FiltraPorOrganizacaoMixin, ProtectedDeleteMixin, DeleteView):
    model = Combo
    template_name = 'cardapio/combo_confirm_delete.html'
    success_url = reverse_lazy('combo_list')
    protected_message = 'Nao e possivel excluir: combo esta em uso em uma ou mais comandas.'


# ---- Mesa CRUD + abertura de comanda ----

class MesaListView(PerfilRequeridoMixin, FiltraPorOrganizacaoMixin, ListView):
    model = Mesa
    template_name = 'cardapio/mesa_list.html'
    context_object_name = 'mesas'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        abertas = {
            c.mesa_id: c
            for c in Comanda.objects.filter(organizacao=org_atual(self.request), status=Comanda.Status.ABERTA)
        }
        context['mesas_com_comanda'] = [(mesa, abertas.get(mesa.id)) for mesa in context['mesas']]
        return context


class MesaCreateView(SomenteAdminMixin, SalvaNaOrganizacaoMixin, CreateView):
    model = Mesa
    form_class = MesaForm
    template_name = 'cardapio/mesa_form.html'
    success_url = reverse_lazy('mesa_list')


class MesaUpdateView(SomenteAdminMixin, FiltraPorOrganizacaoMixin, SalvaNaOrganizacaoMixin, UpdateView):
    model = Mesa
    form_class = MesaForm
    template_name = 'cardapio/mesa_form.html'
    success_url = reverse_lazy('mesa_list')


class MesaDeleteView(SomenteAdminMixin, FiltraPorOrganizacaoMixin, ProtectedDeleteMixin, DeleteView):
    model = Mesa
    template_name = 'cardapio/mesa_confirm_delete.html'
    success_url = reverse_lazy('mesa_list')
    protected_message = 'Nao e possivel excluir: mesa possui comandas vinculadas.'


# ---- Comandas: abrir, itens e fechamento (qualquer perfil; acoes que alteram dados so por POST) ----

class ComandaListView(PerfilRequeridoMixin, FiltraPorOrganizacaoMixin, ListView):
    model = Comanda
    template_name = 'cardapio/comanda_list.html'
    context_object_name = 'comandas'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('mesa')
        status = self.request.GET.get('status', '')
        if status in Comanda.Status.values:
            qs = qs.filter(status=status)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_atual'] = self.request.GET.get('status', '')
        context['status_opcoes'] = Comanda.Status.choices
        return context


@perfil_requerido
@require_POST
def abrir_comanda(request, mesa_id):
    org = org_atual(request)
    mesa = get_object_or_404(Mesa, pk=mesa_id, organizacao=org)
    comanda = mesa.comandas.filter(status=Comanda.Status.ABERTA).first()
    if not comanda:
        comanda = Comanda.objects.create(mesa=mesa, organizacao=org)
    return redirect('comanda_detail', pk=comanda.pk)


def _detalhe_comanda(request, comanda, form):
    return render(request, 'cardapio/comanda_detail.html', {
        'comanda': comanda,
        'itens': comanda.itens.select_related('prato', 'combo'),
        'form': form,
    })


@perfil_requerido
def comanda_detail(request, pk):
    org = org_atual(request)
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=pk, organizacao=org)
    return _detalhe_comanda(request, comanda, ItemComandaForm(org=org))


@perfil_requerido
@require_POST
def adicionar_item(request, comanda_id):
    org = org_atual(request)
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=comanda_id, organizacao=org)
    if comanda.status != Comanda.Status.ABERTA:
        messages.error(request, 'Esta comanda ja esta fechada.')
        return redirect('comanda_detail', pk=comanda.pk)

    form = ItemComandaForm(request.POST, org=org)
    if form.is_valid():
        item = form.save(commit=False)
        item.comanda = comanda
        item.organizacao = org
        item.save()
        messages.success(request, 'Item adicionado a comanda.')
        return redirect('comanda_detail', pk=comanda.pk)
    return _detalhe_comanda(request, comanda, form)


@perfil_requerido
@require_POST
def remover_item(request, item_id):
    item = get_object_or_404(ItemComanda.objects.select_related('comanda'), pk=item_id, organizacao=org_atual(request))
    comanda_id = item.comanda_id
    if item.comanda.status != Comanda.Status.ABERTA:
        messages.error(request, 'Esta comanda ja esta fechada.')
    else:
        item.delete()
        messages.success(request, 'Item removido.')
    return redirect('comanda_detail', pk=comanda_id)


@perfil_requerido
@require_POST
def fechar_comanda(request, comanda_id):
    comanda = get_object_or_404(Comanda, pk=comanda_id, organizacao=org_atual(request))
    if comanda.status == Comanda.Status.ABERTA:
        comanda.fechar()
        messages.success(request, f'Comanda fechada. Total: R$ {comanda.total}')
    return redirect('comanda_detail', pk=comanda.pk)


# ---- Dashboard e relatorio (Aula 17) ----

@perfil_requerido
def dashboard(request):
    org = org_atual(request)
    eh_admin = request.user.perfil.eh_admin
    contexto = metricas.resumo(org, request.GET, incluir_series=eh_admin)
    contexto.update({
        'form': PeriodoForm(request.GET),
        'mostra_series': eh_admin,        # operador ve uma versao parcial
        'pode_exportar': eh_admin,
        'querystring': request.GET.urlencode(),
    })
    return render(request, 'cardapio/dashboard.html', contexto)


def _celula_segura(valor):
    """O Excel interpreta celulas que comecam com = + - @ como formula: neutraliza com um apostrofo."""
    texto = '' if valor is None else str(valor)
    return "'" + texto if texto[:1] in ('=', '+', '-', '@') else texto


@papel_requerido('admin')
def exportar_csv(request):
    org = org_atual(request)
    itens = Prefetch('itens', queryset=ItemComanda.objects.select_related('prato', 'combo'))
    comandas = metricas.comandas_base(org, request.GET).select_related('mesa').prefetch_related(itens)

    resposta = HttpResponse(content_type='text/csv; charset=utf-8')
    resposta['Content-Disposition'] = 'attachment; filename="comandas.csv"'
    resposta.write('﻿')  # BOM: o Excel abre os acentos corretamente
    escritor = csv.writer(resposta)
    escritor.writerow(['Comanda', 'Mesa', 'Status', 'Aberta em', 'Fechada em', 'Itens', 'Total'])
    for c in comandas:
        descricao = '; '.join(f'{i.quantidade}x {i.prato or i.combo}' for i in c.itens.all())
        escritor.writerow([
            c.pk, _celula_segura(c.mesa), c.get_status_display(),
            c.aberta_em.strftime('%d/%m/%Y %H:%M'),
            c.fechada_em.strftime('%d/%m/%Y %H:%M') if c.fechada_em else '',
            _celula_segura(descricao), c.total,
        ])
    return resposta

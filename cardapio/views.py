from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ComboForm, ItemComandaForm, MesaForm, PratoForm
from .models import Combo, Comanda, ItemComanda, Mesa, Prato


class ProtectedDeleteMixin:
    protected_message = 'Nao e possivel excluir: este registro esta vinculado a outros dados.'

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, self.protected_message)
            return redirect(self.success_url)


def cardapio_publico(request):
    pratos = Prato.objects.filter(disponivel=True)
    combos = Combo.objects.filter(disponivel=True).prefetch_related('pratos')
    return render(request, 'cardapio/cardapio_publico.html', {'pratos': pratos, 'combos': combos})


# ---- Prato CRUD ----

class PratoListView(ListView):
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
        return Prato.objects.filter(filtros)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Prato.Categoria.choices
        context['filtrando'] = bool(self.request.GET.get('q', '').strip() or self.request.GET.get('categoria'))
        return context


class PratoCreateView(CreateView):
    model = Prato
    form_class = PratoForm
    template_name = 'cardapio/prato_form.html'
    success_url = reverse_lazy('prato_list')


class PratoUpdateView(UpdateView):
    model = Prato
    form_class = PratoForm
    template_name = 'cardapio/prato_form.html'
    success_url = reverse_lazy('prato_list')


class PratoDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Prato
    template_name = 'cardapio/prato_confirm_delete.html'
    success_url = reverse_lazy('prato_list')
    protected_message = 'Nao e possivel excluir: prato esta em uso em uma ou mais comandas.'


# ---- Combo CRUD ----

class ComboListView(ListView):
    model = Combo
    template_name = 'cardapio/combo_list.html'
    context_object_name = 'combos'


class ComboCreateView(CreateView):
    model = Combo
    form_class = ComboForm
    template_name = 'cardapio/combo_form.html'
    success_url = reverse_lazy('combo_list')


class ComboUpdateView(UpdateView):
    model = Combo
    form_class = ComboForm
    template_name = 'cardapio/combo_form.html'
    success_url = reverse_lazy('combo_list')


class ComboDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Combo
    template_name = 'cardapio/combo_confirm_delete.html'
    success_url = reverse_lazy('combo_list')
    protected_message = 'Nao e possivel excluir: combo esta em uso em uma ou mais comandas.'


# ---- Mesa CRUD + abertura de comanda ----

class MesaListView(ListView):
    model = Mesa
    template_name = 'cardapio/mesa_list.html'
    context_object_name = 'mesas'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        abertas = {c.mesa_id: c for c in Comanda.objects.filter(status=Comanda.Status.ABERTA)}
        context['mesas_com_comanda'] = [(mesa, abertas.get(mesa.id)) for mesa in context['mesas']]
        return context


class MesaCreateView(CreateView):
    model = Mesa
    form_class = MesaForm
    template_name = 'cardapio/mesa_form.html'
    success_url = reverse_lazy('mesa_list')


class MesaUpdateView(UpdateView):
    model = Mesa
    form_class = MesaForm
    template_name = 'cardapio/mesa_form.html'
    success_url = reverse_lazy('mesa_list')


class MesaDeleteView(ProtectedDeleteMixin, DeleteView):
    model = Mesa
    template_name = 'cardapio/mesa_confirm_delete.html'
    success_url = reverse_lazy('mesa_list')
    protected_message = 'Nao e possivel excluir: mesa possui comandas vinculadas.'


def abrir_comanda(request, mesa_id):
    mesa = get_object_or_404(Mesa, pk=mesa_id)
    comanda = mesa.comandas.filter(status=Comanda.Status.ABERTA).first()
    if not comanda:
        comanda = Comanda.objects.create(mesa=mesa)
    return redirect('comanda_detail', pk=comanda.pk)


# ---- Comanda: itens e fechamento ----

def comanda_detail(request, pk):
    comanda = get_object_or_404(Comanda, pk=pk)
    context = {
        'comanda': comanda,
        'itens': comanda.itens.select_related('prato', 'combo'),
        'form': ItemComandaForm(),
    }
    return render(request, 'cardapio/comanda_detail.html', context)


def adicionar_item(request, comanda_id):
    comanda = get_object_or_404(Comanda, pk=comanda_id)
    if comanda.status != Comanda.Status.ABERTA:
        messages.error(request, 'Esta comanda ja esta fechada.')
        return redirect('comanda_detail', pk=comanda.pk)

    if request.method == 'POST':
        form = ItemComandaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.comanda = comanda
            item.save()
            messages.success(request, 'Item adicionado a comanda.')
            return redirect('comanda_detail', pk=comanda.pk)
    else:
        form = ItemComandaForm()

    context = {
        'comanda': comanda,
        'itens': comanda.itens.select_related('prato', 'combo'),
        'form': form,
    }
    return render(request, 'cardapio/comanda_detail.html', context)


def remover_item(request, item_id):
    item = get_object_or_404(ItemComanda, pk=item_id)
    comanda_id = item.comanda_id
    if item.comanda.status != Comanda.Status.ABERTA:
        messages.error(request, 'Esta comanda ja esta fechada.')
    else:
        item.delete()
        messages.success(request, 'Item removido.')
    return redirect('comanda_detail', pk=comanda_id)


def fechar_comanda(request, comanda_id):
    comanda = get_object_or_404(Comanda, pk=comanda_id)
    if comanda.status == Comanda.Status.ABERTA:
        comanda.fechar()
        messages.success(request, f'Comanda fechada. Total: R$ {comanda.total}')
    return redirect('comanda_detail', pk=comanda.pk)

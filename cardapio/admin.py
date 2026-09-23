from django.contrib import admin

from .forms import ComboForm, PratoForm
from .models import Combo, Comanda, ItemComanda, Mesa, Prato


@admin.register(Prato)
class PratoAdmin(admin.ModelAdmin):
    form = PratoForm
    list_display = ('nome', 'categoria', 'preco', 'disponivel')
    list_filter = ('categoria', 'disponivel')
    search_fields = ('nome',)


@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    form = ComboForm
    list_display = ('nome', 'preco', 'disponivel')
    list_filter = ('disponivel',)
    search_fields = ('nome',)
    filter_horizontal = ('pratos',)


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'capacidade')
    search_fields = ('numero',)


class ItemComandaInline(admin.TabularInline):
    model = ItemComanda
    extra = 1


@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = ('id', 'mesa', 'status', 'aberta_em', 'fechada_em', 'total')
    list_filter = ('status',)
    inlines = [ItemComandaInline]
    readonly_fields = ('total', 'fechada_em')

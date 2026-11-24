from django.contrib import admin

from .forms import ComboAdminForm
from .models import Combo, Comanda, ItemComanda, Mesa, Prato


@admin.register(Prato)
class PratoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'organizacao', 'categoria', 'preco', 'disponivel')
    list_filter = ('organizacao', 'categoria', 'disponivel')
    search_fields = ('nome',)


@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    form = ComboAdminForm
    list_display = ('nome', 'organizacao', 'preco', 'disponivel')
    list_filter = ('organizacao', 'disponivel')
    search_fields = ('nome',)
    filter_horizontal = ('pratos',)


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'organizacao', 'capacidade')
    list_filter = ('organizacao',)
    search_fields = ('numero',)


class ItemComandaInline(admin.TabularInline):
    model = ItemComanda
    extra = 1
    # A organizacao do item e sempre a da comanda (definida no save do model).
    exclude = ('organizacao',)


@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = ('id', 'mesa', 'organizacao', 'status', 'aberta_em', 'fechada_em', 'total')
    list_filter = ('organizacao', 'status')
    inlines = [ItemComandaInline]
    readonly_fields = ('total', 'fechada_em')

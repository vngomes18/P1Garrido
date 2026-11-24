from django.urls import path

from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('cardapio/<slug:slug>/', views.cardapio_publico, name='cardapio_publico'),

    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/exportar.csv', views.exportar_csv, name='exportar_csv'),

    path('pratos/', views.PratoListView.as_view(), name='prato_list'),
    path('pratos/novo/', views.PratoCreateView.as_view(), name='prato_create'),
    path('pratos/<int:pk>/editar/', views.PratoUpdateView.as_view(), name='prato_update'),
    path('pratos/<int:pk>/excluir/', views.PratoDeleteView.as_view(), name='prato_delete'),

    path('combos/', views.ComboListView.as_view(), name='combo_list'),
    path('combos/novo/', views.ComboCreateView.as_view(), name='combo_create'),
    path('combos/<int:pk>/editar/', views.ComboUpdateView.as_view(), name='combo_update'),
    path('combos/<int:pk>/excluir/', views.ComboDeleteView.as_view(), name='combo_delete'),

    path('mesas/', views.MesaListView.as_view(), name='mesa_list'),
    path('mesas/nova/', views.MesaCreateView.as_view(), name='mesa_create'),
    path('mesas/<int:pk>/editar/', views.MesaUpdateView.as_view(), name='mesa_update'),
    path('mesas/<int:pk>/excluir/', views.MesaDeleteView.as_view(), name='mesa_delete'),
    path('mesas/<int:mesa_id>/abrir-comanda/', views.abrir_comanda, name='abrir_comanda'),

    path('comandas/', views.ComandaListView.as_view(), name='comanda_list'),
    path('comandas/<int:pk>/', views.comanda_detail, name='comanda_detail'),
    path('comandas/<int:comanda_id>/itens/adicionar/', views.adicionar_item, name='adicionar_item'),
    path('comandas/<int:comanda_id>/fechar/', views.fechar_comanda, name='fechar_comanda'),
    path('itens/<int:item_id>/remover/', views.remover_item, name='remover_item'),
]

from django.urls import path

from . import api_views

urlpatterns = [
    path('pratos/', api_views.PratoListCreate.as_view(), name='api_prato_list'),
    path('pratos/<int:pk>/', api_views.PratoDetail.as_view(), name='api_prato_detail'),

    path('combos/', api_views.ComboListCreate.as_view(), name='api_combo_list'),
    path('combos/<int:pk>/', api_views.ComboDetail.as_view(), name='api_combo_detail'),

    path('mesas/', api_views.MesaListCreate.as_view(), name='api_mesa_list'),
    path('mesas/<int:pk>/', api_views.MesaDetail.as_view(), name='api_mesa_detail'),

    path('comandas/', api_views.ComandaListCreate.as_view(), name='api_comanda_list'),
    path('comandas/<int:pk>/', api_views.ComandaDetail.as_view(), name='api_comanda_detail'),
    path('comandas/<int:pk>/fechar/', api_views.ComandaFechar.as_view(), name='api_comanda_fechar'),
    path('comandas/<int:comanda_id>/itens/', api_views.ItemCreate.as_view(), name='api_item_create'),
    path('itens/<int:pk>/', api_views.ItemDestroy.as_view(), name='api_item_detail'),

    path('dashboard/', api_views.DashboardApi.as_view(), name='api_dashboard'),
]

"""Organizacao atual e controle de acesso por papel (paginas e API).

Regra de ouro (Aula 14): a organizacao SEMPRE vem do usuario logado, nunca da
URL nem de formulario.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from rest_framework import permissions

from .models import Perfil


def perfil_do_usuario(user):
    """Devolve o Perfil ou None (superusuario sem perfil, por exemplo)."""
    return getattr(user, 'perfil', None)


def org_atual(request):
    return request.user.perfil.organizacao


# ---- Paginas (views baseadas em funcao) ----

def perfil_requerido(view):
    """Exige login E perfil. Quem esta logado sem perfil recebe 403 (e nao um erro 500)."""
    @wraps(view)
    @login_required
    def envelope(request, *args, **kwargs):
        if perfil_do_usuario(request.user) is None:
            raise PermissionDenied('Usuario sem perfil de organizacao.')
        return view(request, *args, **kwargs)
    return envelope


def papel_requerido(*papeis):
    """Exige login, perfil e um dos papeis informados. Ex.: @papel_requerido('admin')."""
    def decorador(view):
        @wraps(view)
        @perfil_requerido
        def envelope(request, *args, **kwargs):
            if request.user.perfil.papel not in papeis:
                raise PermissionDenied('Seu papel nao permite esta acao.')
            return view(request, *args, **kwargs)
        return envelope
    return decorador


# ---- Paginas (views baseadas em classe) ----

class PerfilRequeridoMixin(LoginRequiredMixin):
    """Login + perfil. Defina `papeis_permitidos` para restringir por papel."""

    papeis_permitidos = None  # None = qualquer papel

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        perfil = perfil_do_usuario(request.user)
        if perfil is None:
            raise PermissionDenied('Usuario sem perfil de organizacao.')
        if self.papeis_permitidos and perfil.papel not in self.papeis_permitidos:
            raise PermissionDenied('Seu papel nao permite esta acao.')
        return super().dispatch(request, *args, **kwargs)


class SomenteAdminMixin(PerfilRequeridoMixin):
    papeis_permitidos = (Perfil.ADMIN,)


# ---- API (DRF) ----

class TemPerfil(permissions.BasePermission):
    """Autenticado e com perfil. Sem perfil nao ha organizacao, logo nao ha dados."""

    message = 'Usuario sem perfil de organizacao.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and perfil_do_usuario(user))


class AdminEscreveOperadorLe(TemPerfil):
    """Leitura para qualquer perfil; escrita (POST/PUT/PATCH/DELETE) so para administrador."""

    message = 'Apenas administradores podem alterar este recurso.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.perfil.eh_admin


class ApenasAdmin(TemPerfil):
    message = 'Apenas administradores podem acessar este recurso.'

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.perfil.eh_admin

from django.contrib.auth.models import User
from django.db import models
from django.utils.text import slugify


class Organizacao(models.Model):
    """O 'inquilino' do sistema: dona dos dados (um restaurante, por exemplo)."""

    nome = models.CharField(max_length=120)
    # Usado na URL publica do cardapio (/cardapio/<slug>/).
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Organizacao'
        verbose_name_plural = 'Organizacoes'

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)


class DaOrganizacao(models.Model):
    """Base abstrata: todo model com dados de negocio herda a FK da organizacao."""

    organizacao = models.ForeignKey('core.Organizacao', on_delete=models.PROTECT)

    class Meta:
        abstract = True


class Perfil(models.Model):
    """Liga o usuario a UMA organizacao e define o papel dele."""

    ADMIN = 'admin'
    OPERADOR = 'operador'
    PAPEIS = [(ADMIN, 'Administrador'), (OPERADOR, 'Operador')]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    organizacao = models.ForeignKey(Organizacao, on_delete=models.PROTECT)
    papel = models.CharField(max_length=20, choices=PAPEIS, default=OPERADOR)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfis'

    def __str__(self):
        return f'{self.usuario} - {self.organizacao} ({self.get_papel_display()})'

    @property
    def eh_admin(self):
        return self.papel == self.ADMIN

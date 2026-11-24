from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from core.models import DaOrganizacao

from .validators import preco_combo_positivo, preco_prato_positivo


class Prato(DaOrganizacao):
    class Categoria(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        PRINCIPAL = 'PRINCIPAL', 'Prato principal'
        ACOMPANHAMENTO = 'ACOMPANHAMENTO', 'Acompanhamento'
        BEBIDA = 'BEBIDA', 'Bebida'
        SOBREMESA = 'SOBREMESA', 'Sobremesa'

    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.PRINCIPAL)
    preco = models.DecimalField(max_digits=8, decimal_places=2, validators=[preco_prato_positivo])
    disponivel = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Prato'
        verbose_name_plural = 'Pratos'

    def __str__(self):
        return self.nome


class Combo(DaOrganizacao):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=8, decimal_places=2, validators=[preco_combo_positivo])
    pratos = models.ManyToManyField(Prato, related_name='combos')
    disponivel = models.BooleanField(default=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Combo'
        verbose_name_plural = 'Combos'

    def __str__(self):
        return self.nome


class Mesa(DaOrganizacao):
    numero = models.PositiveIntegerField()
    capacidade = models.PositiveIntegerField(default=4)

    class Meta:
        ordering = ['numero']
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        constraints = [
            # Duas organizacoes podem ter a "Mesa 1"; a mesma organizacao nao pode ter duas.
            models.UniqueConstraint(fields=['organizacao', 'numero'], name='mesa_numero_unico_por_org'),
        ]

    def __str__(self):
        return f'Mesa {self.numero}'

    @property
    def comanda_aberta(self):
        return self.comandas.filter(status=Comanda.Status.ABERTA).first()


class Comanda(DaOrganizacao):
    class Status(models.TextChoices):
        ABERTA = 'ABERTA', 'Aberta'
        FECHADA = 'FECHADA', 'Fechada'

    mesa = models.ForeignKey(Mesa, on_delete=models.PROTECT, related_name='comandas')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)
    aberta_em = models.DateTimeField(auto_now_add=True)
    fechada_em = models.DateTimeField(null=True, blank=True)
    total = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['-aberta_em']
        verbose_name = 'Comanda'
        verbose_name_plural = 'Comandas'
        constraints = [
            models.UniqueConstraint(
                fields=['mesa'],
                condition=models.Q(status='ABERTA'),
                name='uma_comanda_aberta_por_mesa',
            ),
        ]

    def __str__(self):
        return f'Comanda #{self.pk} - Mesa {self.mesa.numero}'

    def calcular_total(self):
        return sum((item.subtotal for item in self.itens.all()), Decimal('0.00'))

    def fechar(self):
        from django.utils import timezone

        if self.status == self.Status.FECHADA:
            raise ValidationError('Esta comanda ja esta fechada.')
        self.total = self.calcular_total()
        self.status = self.Status.FECHADA
        self.fechada_em = timezone.now()
        self.save(update_fields=['total', 'status', 'fechada_em'])


class ItemComanda(DaOrganizacao):
    comanda = models.ForeignKey(Comanda, on_delete=models.CASCADE, related_name='itens')
    prato = models.ForeignKey(Prato, on_delete=models.PROTECT, null=True, blank=True)
    combo = models.ForeignKey(Combo, on_delete=models.PROTECT, null=True, blank=True)
    quantidade = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ['id']
        verbose_name = 'Item da Comanda'
        verbose_name_plural = 'Itens da Comanda'
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(prato__isnull=False, combo__isnull=True)
                    | models.Q(prato__isnull=True, combo__isnull=False)
                ),
                name='item_deve_ter_prato_ou_combo',
            ),
        ]

    def __str__(self):
        return f'{self.quantidade}x {self.prato or self.combo}'

    def clean(self):
        if bool(self.prato_id) == bool(self.combo_id):
            raise ValidationError('Informe um prato ou um combo, nao ambos nem nenhum.')
        produto = self.prato or self.combo
        if self.comanda_id and produto.organizacao_id != self.comanda.organizacao_id:
            raise ValidationError('O item deve pertencer a mesma organizacao da comanda.')

    def save(self, *args, **kwargs):
        if self.preco_unitario is None:
            self.preco_unitario = (self.prato or self.combo).preco
        if not self.organizacao_id:
            # A organizacao do item e sempre a da comanda: nunca vem de fora.
            self.organizacao_id = self.comanda.organizacao_id
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.preco_unitario * self.quantidade

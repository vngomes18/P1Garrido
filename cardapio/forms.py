from django import forms
from django.core.exceptions import ValidationError

from .models import Combo, ItemComanda, Mesa, Prato
from .validators import validar_desconto_combo


class PratoForm(forms.ModelForm):
    # A regra "preco > 0" vive no model (validators.py): vale aqui, no Admin e na API.
    class Meta:
        model = Prato
        fields = ['nome', 'descricao', 'categoria', 'preco', 'disponivel']

    def __init__(self, *args, org=None, **kwargs):
        # Sem campos relacionados, `org` nao filtra nada; o parametro existe para que
        # todas as views criem os formularios do mesmo jeito.
        super().__init__(*args, **kwargs)


class ComboForm(forms.ModelForm):
    class Meta:
        model = Combo
        fields = ['nome', 'descricao', 'preco', 'pratos', 'disponivel']
        widgets = {'pratos': forms.CheckboxSelectMultiple}

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)
        if org is not None:
            # Todo select/M2M do formulario so mostra opcoes da organizacao (Aula 14).
            self.fields['pratos'].queryset = Prato.objects.filter(organizacao=org)
        # Mostra o preco de cada prato para facilitar o calculo do preco do combo.
        self.fields['pratos'].label_from_instance = lambda prato: f'{prato.nome} (R$ {prato.preco})'

    def clean(self):
        cleaned_data = super().clean()
        try:
            validar_desconto_combo(cleaned_data.get('preco'), cleaned_data.get('pratos'))
        except ValidationError as erro:
            self.add_error('preco', erro)
        return cleaned_data


class ComboAdminForm(ComboForm):
    """Mesma regra de desconto no Django Admin (la a organizacao e escolhida no formulario)."""

    class Meta(ComboForm.Meta):
        fields = ComboForm.Meta.fields + ['organizacao']
        widgets = {}


class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'capacidade']

    def __init__(self, *args, org=None, **kwargs):
        self.org = org
        super().__init__(*args, **kwargs)

    def clean_numero(self):
        # A organizacao nao esta no formulario, entao o Django nao valida a restricao
        # de unicidade por organizacao: tratamos aqui para nao estourar IntegrityError.
        numero = self.cleaned_data['numero']
        if self.org is not None:
            duplicadas = Mesa.objects.filter(organizacao=self.org, numero=numero)
            if self.instance.pk:
                duplicadas = duplicadas.exclude(pk=self.instance.pk)
            if duplicadas.exists():
                raise forms.ValidationError('Ja existe uma mesa com este numero.')
        return numero


class ItemComandaForm(forms.ModelForm):
    class Meta:
        model = ItemComanda
        fields = ['prato', 'combo', 'quantidade']

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)
        pratos, combos = Prato.objects.filter(disponivel=True), Combo.objects.filter(disponivel=True)
        if org is not None:
            pratos, combos = pratos.filter(organizacao=org), combos.filter(organizacao=org)
        self.fields['prato'].queryset = pratos
        self.fields['prato'].required = False
        self.fields['combo'].queryset = combos
        self.fields['combo'].required = False

    def clean(self):
        cleaned_data = super().clean()
        prato = cleaned_data.get('prato')
        combo = cleaned_data.get('combo')
        if bool(prato) == bool(combo):
            raise forms.ValidationError('Selecione um prato ou um combo, nao ambos nem nenhum.')
        return cleaned_data


class PeriodoForm(forms.Form):
    """Filtro de periodo do dashboard: valida as datas da URL (uma data invalida nao gera erro 500)."""

    inicio = forms.DateField(required=False, label='De', widget=forms.DateInput(attrs={'type': 'date'}))
    fim = forms.DateField(required=False, label='Ate', widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        cleaned_data = super().clean()
        inicio, fim = cleaned_data.get('inicio'), cleaned_data.get('fim')
        if inicio and fim and inicio > fim:
            raise forms.ValidationError('A data inicial nao pode ser depois da data final.')
        return cleaned_data

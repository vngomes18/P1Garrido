from django import forms

from .models import Combo, ItemComanda, Mesa, Prato


class PratoForm(forms.ModelForm):
    class Meta:
        model = Prato
        fields = ['nome', 'descricao', 'preco', 'disponivel']


class ComboForm(forms.ModelForm):
    class Meta:
        model = Combo
        fields = ['nome', 'descricao', 'preco', 'pratos', 'disponivel']
        widgets = {'pratos': forms.CheckboxSelectMultiple}


class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero', 'capacidade']


class ItemComandaForm(forms.ModelForm):
    class Meta:
        model = ItemComanda
        fields = ['prato', 'combo', 'quantidade']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['prato'].queryset = Prato.objects.filter(disponivel=True)
        self.fields['prato'].required = False
        self.fields['combo'].queryset = Combo.objects.filter(disponivel=True)
        self.fields['combo'].required = False

    def clean(self):
        cleaned_data = super().clean()
        prato = cleaned_data.get('prato')
        combo = cleaned_data.get('combo')
        if bool(prato) == bool(combo):
            raise forms.ValidationError('Selecione um prato ou um combo, nao ambos nem nenhum.')
        return cleaned_data

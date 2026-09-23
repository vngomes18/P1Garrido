from decimal import ROUND_DOWN, ROUND_UP, Decimal

from django import forms

from .models import Combo, ItemComanda, Mesa, Prato


class PratoForm(forms.ModelForm):
    class Meta:
        model = Prato
        fields = ['nome', 'descricao', 'categoria', 'preco', 'disponivel']

    def clean_preco(self):
        preco = self.cleaned_data.get('preco')
        # Um prato com preco zero ou negativo zeraria/abateria o total da comanda no fechamento.
        if preco is not None and preco <= 0:
            raise forms.ValidationError('O preco do prato deve ser maior que zero.')
        return preco


class ComboForm(forms.ModelForm):
    # O combo precisa sair entre 10% e 15% mais barato que a soma dos pratos pedidos separadamente.
    DESCONTO_MINIMO = Decimal('0.10')
    DESCONTO_MAXIMO = Decimal('0.15')

    class Meta:
        model = Combo
        fields = ['nome', 'descricao', 'preco', 'pratos', 'disponivel']
        widgets = {'pratos': forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mostra o preco de cada prato para facilitar o calculo do preco do combo.
        self.fields['pratos'].label_from_instance = lambda prato: f'{prato.nome} (R$ {prato.preco})'

    def clean_preco(self):
        preco = self.cleaned_data.get('preco')
        if preco is not None and preco <= 0:
            raise forms.ValidationError('O preco do combo deve ser maior que zero.')
        return preco

    def clean(self):
        cleaned_data = super().clean()
        preco = cleaned_data.get('preco')
        pratos = cleaned_data.get('pratos')
        if preco is None or not pratos:
            return cleaned_data

        soma = sum((prato.preco for prato in pratos), Decimal('0.00'))
        preco_maximo = soma * (1 - self.DESCONTO_MINIMO)
        preco_minimo = soma * (1 - self.DESCONTO_MAXIMO)
        if not preco_minimo <= preco <= preco_maximo:
            centavo = Decimal('0.01')
            self.add_error('preco', forms.ValidationError(
                f'O combo deve ter de 10% a 15% de desconto sobre a soma dos pratos '
                f'(R$ {soma.quantize(centavo)}). Informe um preco entre '
                f'R$ {preco_minimo.quantize(centavo, rounding=ROUND_UP)} e '
                f'R$ {preco_maximo.quantize(centavo, rounding=ROUND_DOWN)}.'
            ))
        return cleaned_data


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

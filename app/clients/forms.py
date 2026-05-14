from django import forms
from .models import Client, Order


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['nom', 'telephone', 'email']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom complet'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+254 700 000 000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemple.com'}),
        }


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['client', 'nom_produit', 'quantite', 'prix_total']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-control'}),
            'nom_produit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du produit'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1', 'min': '1', 'value': '1'}),
            'prix_total': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
        }

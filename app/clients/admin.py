from django.contrib import admin
from .models import Client, Order


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['nom', 'telephone', 'email', 'odoo_partner_id']
    search_fields = ['nom', 'email', 'telephone']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['nom_produit', 'client', 'prix_total', 'odoo_order_id', 'created_at']
    list_filter = ['client']
    search_fields = ['nom_produit', 'client__nom']

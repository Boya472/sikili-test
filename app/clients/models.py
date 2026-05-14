from django.db import models


class Client(models.Model):
    nom = models.CharField(max_length=200)
    telephone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    odoo_partner_id = models.IntegerField(null=True, blank=True)

    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Order(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='orders')
    nom_produit = models.CharField(max_length=300)
    quantite = models.PositiveIntegerField(default=1)
    prix_total = models.DecimalField(max_digits=10, decimal_places=2)
    odoo_order_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nom_produit} - {self.client.nom}"

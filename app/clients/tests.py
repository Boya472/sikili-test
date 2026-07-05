from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Client
from .odoo_service import OdooService, OdooError


ODOO_SETTINGS = dict(
    ODOO_URL='http://localhost:8069',
    ODOO_DB='test_db',
    ODOO_USER='admin',
    ODOO_PASSWORD='admin',
)


@override_settings(**ODOO_SETTINGS)
class OdooServiceCreatePartnerTest(TestCase):

    def test_create_partner_success(self):
        """create_partner retourne l'ID Odoo quand l'appel réussit."""
        with patch.object(OdooService, 'authenticate', return_value=42), \
             patch.object(OdooService, '_call_kw', return_value=123) as mock_call_kw:
            service = OdooService()
            result = service.create_partner('Alice Dupont', '0600000000', 'alice@test.com')

        self.assertEqual(result, 123)
        mock_call_kw.assert_called_once_with('res.partner', 'create', [{
           'name': 'Alice Dupont',
           'phone': '0600000000',
           'email': 'alice@test.com',
            'customer_rank': 1,
    }])

    def test_create_partner_odoo_error(self):
        """create_partner retourne None quand Odoo signale une erreur."""
        with patch.object(OdooService, 'authenticate', return_value=42), \
             patch.object(OdooService, '_call_kw', side_effect=OdooError('Erreur Odoo simulée')):
            service = OdooService()
            result = service.create_partner('Alice Dupont', '0600000000', 'alice@test.com')

        self.assertIsNone(result)


@override_settings(**ODOO_SETTINGS)
class OdooServiceCreateSaleOrderTest(TestCase):

    def test_create_sale_order_success(self):
        """create_sale_order retourne l'ID Odoo de la commande quand l'appel réussit."""
        with patch.object(OdooService, 'authenticate', return_value=42), \
             patch.object(OdooService, '_get_currency_id', return_value=5), \
             patch.object(OdooService, '_call_kw', return_value=456) as mock_call_kw:
            service = OdooService()
            result = service.create_sale_order(
                odoo_partner_id=1,
                nom_produit='Café Premium',
                prix_total=10000,
                quantite=2,
                order_id=7,
            )

        self.assertEqual(result, 456)
        args, _ = mock_call_kw.call_args
        self.assertEqual(args[0], 'sale.order')
        self.assertEqual(args[1], 'create')
        order_data = args[2][0]
        self.assertEqual(order_data['partner_id'], 1)
        self.assertEqual(order_data['currency_id'], 5)
        line = order_data['order_line'][0][2]
        self.assertEqual(line['name'], 'Café Premium')
        self.assertEqual(line['product_uom_qty'], 2)
        self.assertAlmostEqual(line['price_unit'], 5000.0)


class ListeClientsViewTest(TestCase):

    def test_liste_clients_vide(self):
        """La vue liste_clients répond 200 et affiche zéro client quand la base est vide."""
        response = self.client.get(reverse('liste_clients'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['count_total'], 0)
        self.assertEqual(list(response.context['clients']), [])


@override_settings(**ODOO_SETTINGS)
class CreerClientViewTest(TestCase):

    def test_creer_client_form_valide(self):
        """Un POST valide crée le client en base, le synchronise avec Odoo et redirige."""
        with patch('clients.views.OdooService') as MockService:
            MockService.return_value.create_partner.return_value = 99
            response = self.client.post(reverse('creer_client'), {
                'nom': 'Jean Dupont',
                'telephone': '0600000000',
                'email': 'jean@test.com',
            })

        self.assertRedirects(response, reverse('liste_clients'))
        client = Client.objects.get(email='jean@test.com')
        self.assertEqual(client.nom, 'Jean Dupont')
        self.assertEqual(client.odoo_partner_id, 99)

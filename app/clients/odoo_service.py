import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OdooService:
    """Client JSON-RPC pour l'API Odoo."""

    def __init__(self):
        self.url = settings.ODOO_URL.rstrip('/')
        self.db = settings.ODOO_DB
        self.user = settings.ODOO_USER
        self.password = settings.ODOO_PASSWORD
        self.session = requests.Session()
        self._uid = None

    # ------------------------------------------------------------------
    # Helpers internes
    # ------------------------------------------------------------------

    def _call(self, endpoint, params):
        """Envoie une requête JSON-RPC et retourne le champ 'result'."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": 1,
            "params": params,
        }
        response = self.session.post(
            f"{self.url}{endpoint}",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            msg = data["error"].get("data", {}).get("message") or str(data["error"])
            raise OdooError(msg)

        return data["result"]

    def _call_kw(self, model, method, args, kwargs=None):
        """Raccourci pour les appels /web/dataset/call_kw."""
        return self._call("/web/dataset/call_kw", {
            "model": model,
            "method": method,
            "args": args,
            "kwargs": kwargs or {},
        })

    def _get_currency_id(self, currency_code):
        """Récupère l'ID d'une devise par son code (ex: 'XOF', 'EUR', 'USD')."""
        try:
            result = self._call_kw("res.currency", "search", [
                ["code", "=", currency_code]
            ])
            if result:
                return result[0]
            logger.warning("Odoo — devise %s non trouvée", currency_code)
            return None
        except (OdooError, requests.RequestException) as exc:
            logger.error("Odoo — erreur recherche devise %s : %s", currency_code, exc)
            return None

    # ------------------------------------------------------------------
    # Méthodes publiques
    # ------------------------------------------------------------------

    def authenticate(self):
        """
        Authentifie la session auprès d'Odoo.
        Retourne l'uid (int) en cas de succès, None en cas d'échec.
        """
        try:
            result = self._call("/web/session/authenticate", {
                "db": self.db,
                "login": self.user,
                "password": self.password,
            })
            uid = result.get("uid")
            if not uid:
                raise OdooError("Authentification échouée : identifiants invalides.")
            self._uid = uid
            logger.info("Odoo — authentifié avec uid=%s", uid)
            return uid
        except OdooError as exc:
            logger.error("Odoo — erreur d'authentification : %s", exc)
            return None
        except requests.RequestException as exc:
            logger.error("Odoo — connexion impossible (%s) : %s", self.url, exc)
            return None

    def create_partner(self, nom, telephone, email):
        """
        Crée un res.partner dans Odoo.
        Retourne l'id Odoo du partenaire, ou None en cas d'échec.
        """
        if not self._uid and not self.authenticate():
            return None
        try:
            partner_id = self._call_kw("res.partner", "create", [{
                "name": nom,
                "phone": telephone,
                "email": email,
                "customer_rank": 1,
                "x_sikili_source": "Sikili Web App",
            }])
            logger.info("Odoo — partenaire créé : id=%s, nom=%s", partner_id, nom)
            return partner_id
        except OdooError as exc:
            logger.error("Odoo — erreur création partenaire '%s' : %s", nom, exc)
            return None
        except requests.RequestException as exc:
            logger.error("Odoo — erreur réseau lors de la création du partenaire : %s", exc)
            return None

    def create_sale_order(self, odoo_partner_id, nom_produit, prix_total, quantite=1, order_id=None):
        """
        Crée un sale.order dans Odoo lié au partenaire donné.
        Retourne l'id Odoo de la commande, ou None en cas d'échec.
        """
        if not self._uid and not self.authenticate():
            return None
        try:
            sikili_ref = f"SIKILI-{order_id}" if order_id else "SIKILI"
            xof_currency_id = self._get_currency_id("XOF")
            prix_unitaire = float(prix_total) / quantite

            order_data = {
                "partner_id": odoo_partner_id,
                "x_sikili_ref": sikili_ref,
                "order_line": [(0, 0, {
                    "name": nom_produit,
                    "price_unit": prix_unitaire,
                    "product_uom_qty": quantite,
                })],
            }
            if xof_currency_id:
                order_data["currency_id"] = xof_currency_id

            odoo_order_id = self._call_kw("sale.order", "create", [order_data])
            logger.info(
                "Odoo — commande créée : id=%s, partenaire=%s, produit=%s, devise=XOF",
                odoo_order_id, odoo_partner_id, nom_produit,
            )
            return odoo_order_id
        except OdooError as exc:
            logger.error(
                "Odoo — erreur création commande (partenaire=%s, produit=%s) : %s",
                odoo_partner_id, nom_produit, exc,
            )
            return None
        except requests.RequestException as exc:
            logger.error("Odoo — erreur réseau lors de la création de la commande : %s", exc)
            return None


class OdooError(Exception):
    """Erreur retournée par l'API JSON-RPC d'Odoo."""

# Sikili — Synchronisation Web / Odoo 18

## Présentation

Application web Django qui synchronise automatiquement les clients et commandes avec une instance Odoo 18 via l'API JSON-RPC. Chaque client créé sur la plateforme web apparaît instantanément dans Odoo comme `res.partner`, et chaque commande comme `sale.order` lié au bon partenaire — sans double saisie.

---

## Prérequis

- Docker Desktop installé et démarré
- Git

---

## Lancer le projet localement

```bash
# 1. Cloner le repo
git clone <https://github.com/Boya472/sikili-test.git>
cd sikili-test

# 2. Copier le fichier d'environnement
cp .env.example .env

# 3. Lancer tous les services
docker compose up --build

# 4. Appliquer les migrations Django
docker compose exec app python manage.py migrate

# 5. Accéder à l'application
# App web : http://localhost:8000
# Odoo    : http://localhost:8070
```

---

## Connexion Odoo

- **URL** : https://odoo-18-0-atcc.onrender.com
- **Login** : admin
- **Mot de passe** : admin

---

## Installer le module personnalisé Sikili Connector

1. Aller dans **Apps** dans Odoo
2. Cliquer sur **"Mettre à jour la liste des Apps"**
3. Chercher **"Sikili Connector"**
4. Cliquer sur **"Installer"**

---

## Objets Odoo utilisés et justification

### `res.partner` — Clients

`res.partner` est le modèle universel d'Odoo pour tout contact — client, fournisseur ou employé. Nous aurions pu utiliser `res.users` mais ce modèle est réservé aux personnes qui se connectent à Odoo. Nos clients web n'ont pas besoin de se connecter à Odoo — ils sont simplement des contacts. `res.partner` est donc le choix naturel et standard pour représenter un client.

### `sale.order` — Commandes

`sale.order` est le modèle standard pour les commandes de vente dans Odoo. Nous aurions pu utiliser `account.invoice` directement mais une facture suppose qu'une commande a déjà été passée et validée. Le flux naturel dans Odoo est : **Commande (`sale.order`) → Livraison → Facture (`account.invoice`)**. Créer une facture sans commande aurait cassé ce flux métier.

### `sale.order.line` — Lignes de commande

Chaque commande contient des lignes de détail — produit, quantité, prix unitaire. `sale.order.line` est le modèle qui stocke ces informations et les lie à la commande parente. Sans `sale.order.line`, une commande Odoo serait vide et inexploitable.

---

## Pourquoi JSON-RPC et pas XML-RPC

Odoo expose deux protocoles d'API : JSON-RPC et XML-RPC. Nous avons choisi JSON-RPC car :

- Plus léger et moderne que XML-RPC
- Ne nécessite que la bibliothèque `requests` — pas de dépendance supplémentaire
- Les réponses JSON sont faciles à lire et à déboguer
- XML-RPC est plus verbeux, plus lent et plus ancien

---

## Architecture — Séparation des responsabilités

Tous les appels à l'API Odoo sont isolés dans `app/clients/odoo_service.py`. Les vues Django ne parlent jamais directement à Odoo — elles passent toujours par la classe `OdooService`.

**Avantages :**

- Si Odoo change son API → on modifie uniquement `odoo_service.py`
- Code plus lisible, maintenable et testable
- Séparation claire entre logique métier Django et intégration Odoo

---

## Module Odoo personnalisé — `sikili_connector`

Le module `sikili_connector` ajoute deux champs de traçabilité :

- `x_sikili_source` sur `res.partner` — indique que le client vient de l'application web Sikili
- `x_sikili_ref` sur `sale.order` — référence de la commande Django dans Odoo (ex: `SIKILI-42`)

Ces champs permettent à l'équipe Sikili de filtrer et identifier facilement les clients et commandes qui proviennent de la plateforme web.

---

## Hypothèses et simplifications

- Odoo 18 Community — pas Enterprise
- PostgreSQL partagé entre Django et Odoo dans le même container Docker
- Pas d'authentification utilisateur côté Django — interface interne
- La devise est configurée en XOF dans `odoo_service.py` mais dépend de la configuration Odoo

---

## Blocages rencontrés et explications

### 1. Les commandes restent en statut Devis dans Odoo

Les commandes créées depuis l'app web apparaissent en statut **Devis** (`sale.order` non confirmé) et non en **Commande client** confirmée. La raison : pour confirmer automatiquement une commande dans Odoo, chaque ligne de commande (`sale.order.line`) doit être liée à un produit existant dans le catalogue Odoo via `product.product`. Notre app accepte un nom de produit en texte libre — Odoo ne peut pas le lier automatiquement à son catalogue.

**Comment le résoudre avec plus de temps :** ajouter une méthode `get_products()` dans `OdooService` pour récupérer la liste des produits depuis Odoo, afficher une liste déroulante dans le formulaire de commande, et appeler `action_confirm` après la création du `sale.order`.

### 2. Base de données Odoo non initialisée au démarrage

Odoo démarrait mais retournait `relation ir_module_module does not exist`. La base PostgreSQL existait mais Odoo n'avait jamais installé son schéma.

**Solution :**
```bash
odoo -d sikili_db -i base --stop-after-init --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo
```

### 3. Vue XML Odoo — xpath incorrect

Le module `sikili_connector` utilisait `//page[@name='extra']` qui n'existe pas dans Odoo 18.

**Solution :** utiliser `//field[@name='website']` comme point d'ancrage.

---

## Fonctionnalités implémentées

- Création et synchronisation automatique des clients vers Odoo (`res.partner`)
- Création et synchronisation automatique des commandes vers Odoo (`sale.order` + `sale.order.line`)
- Statut de synchronisation visible en temps réel dans l'interface
- Resynchronisation manuelle des clients non synchronisés
- Bouton **"Synchroniser tout"** pour resynchroniser tous les clients en une fois
- Filtres par statut : Tous / Synchronisé / Non synchronisé
- Barre de recherche par nom, email ou téléphone
- Pagination de la liste des clients
- Champs de traçabilité Odoo via module personnalisé `sikili_connector`
- Gestion des erreurs — le client est sauvegardé localement même si Odoo est indisponible

---

## Tests unitaires

Le projet inclut 5 tests unitaires dans `app/clients/tests.py` :

| Test | Description |
|------|-------------|
| `test_create_partner_success` | Vérifie que `create_partner` retourne l'ID Odoo quand l'appel réussit |
| `test_create_partner_odoo_error` | Vérifie que `create_partner` retourne `None` en cas d'erreur Odoo |
| `test_create_sale_order_success` | Vérifie que `create_sale_order` retourne l'ID Odoo de la commande |
| `test_liste_clients_vide` | Vérifie que la vue `liste_clients` répond 200 avec une liste vide |
| `test_creer_client_form_valide` | Vérifie que la création d'un client fonctionne et redirige |

Pour lancer les tests :

```bash
cd app
python manage.py test clients.tests --verbosity=2
```

Les tests utilisent SQLite en mémoire — pas besoin que Docker soit démarré.

---

## Améliorations futures

- Confirmation automatique des commandes via sélection de produits du catalogue Odoo
- Resynchronisation automatique via tâche Celery périodique
- Authentification utilisateur Django
- Séparation des bases Django et Odoo en production

---

## Utilisation de l'IA

Ce projet a été développé avec l'assistance de deux outils IA complémentaires :

**Claude AI (claude.ai)** a été utilisé pour :
- La réflexion sur l'architecture et les choix techniques
- Les explications sur les modèles Odoo (`res.partner`, `sale.order`, JSON-RPC)
- La clarification de la logique métier
- La rédaction des prompts envoyés à Claude Code
- La compréhension et la validation de chaque décision technique

**Claude Code** a été utilisé pour :
- L'exécution des prompts rédigés avec Claude AI
- La génération du code Django, des templates HTML et du module Odoo
- Le débogage des erreurs techniques
- Les modifications et améliorations du code

Chaque suggestion de l'IA a été lue, comprise et validée avant implémentation. Les échanges clés avec Claude AI sont documentés dans le fichier `AI_SESSION.md`.

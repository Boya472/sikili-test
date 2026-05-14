# Journal de Session IA — Projet Sikili

## Outils utilisés
- Claude AI (claude.ai) — réflexion, architecture, explications techniques, rédaction des prompts
- Claude Code — exécution des prompts, génération du code, débogage

## Répartition des rôles
Claude AI a joué le rôle de chef de projet et architecte : comprendre les exigences, expliquer la logique Odoo, concevoir l'architecture et rédiger les prompts. Claude Code a joué le rôle d'implémenteur : exécuter les prompts et générer le code Django, les templates HTML et le module Odoo. La développeuse a validé chaque décision avant implémentation.

Voir capture : Afficher l'image

## Décisions techniques clés et captures

### 1. Choix de res.partner pour les clients
res.partner est le modèle universel Odoo pour tout contact. Nous aurions pu utiliser res.users mais c'est réservé aux utilisateurs qui se connectent à Odoo. Nos clients web n'ont pas besoin de se connecter.



### 2. Choix de sale.order pour les commandes
sale.order est le modèle standard pour les commandes de vente. account.invoice est pour les factures — or une facture suppose qu'une commande a déjà été passée. Le flux naturel est : Commande → Livraison → Facture.

A

### 3. Choix de JSON-RPC vs XML-RPC
JSON-RPC est plus léger, moderne et ne nécessite que la bibliothèque requests. XML-RPC est plus verbeux et plus lent.



### 4. Architecture couche service odoo_service.py
Tous les appels Odoo sont isolés dans odoo_service.py. Les vues Django ne parlent jamais directement à Odoo.



### 5. Sécurité avec le fichier .env
Les mots de passe ne sont jamais dans le code — ils sont dans .env qui reste sur le PC et n'est pas poussé sur GitHub.



### 6. Module sikili_connector — Traçabilité
Le module ajoute x_sikili_source sur res.partner et x_sikili_ref sur sale.order pour identifier l'origine des données.


### 7. Prompts envoyés à Claude Code
Exemple de prompt envoyé à Claude Code pour créer l'application Django :




import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Subquery, OuterRef, DateTimeField, Exists

from .models import Client, Order
from .forms import ClientForm, OrderForm
from .odoo_service import OdooService

logger = logging.getLogger(__name__)


def liste_clients(request):
    q = request.GET.get('q', '').strip()
    filtre = request.GET.get('filtre', 'tous')

    # Sous-requête : le client a-t-il au moins une commande non synchronisée ?
    has_unsynced_sq = Order.objects.filter(
        client=OuterRef('pk'),
        odoo_order_id__isnull=True,
    )
    # Sous-requête : date de la dernière commande synchronisée du client
    last_sync_sq = Order.objects.filter(
        client=OuterRef('pk'),
        odoo_order_id__isnull=False,
    ).order_by('-created_at').values('created_at')[:1]

    # "Synchronisé" = partenaire Odoo présent ET aucune commande non synchronisée
    base = Client.objects.annotate(has_unsynced_order=Exists(has_unsynced_sq))
    count_total    = base.count()
    count_sync     = base.filter(odoo_partner_id__isnull=False, has_unsynced_order=False).count()
    count_non_sync = base.filter(Q(odoo_partner_id__isnull=True) | Q(has_unsynced_order=True)).count()

    qs = Client.objects.prefetch_related('orders').annotate(
        has_unsynced_order=Exists(has_unsynced_sq),
        last_sync_at=Subquery(last_sync_sq, output_field=DateTimeField()),
        total_commandes=Sum('orders__prix_total'),
    )

    if q:
        qs = qs.filter(
            Q(nom__icontains=q) | Q(email__icontains=q) | Q(telephone__icontains=q)
        )

    if filtre == 'sync':
        qs = qs.filter(odoo_partner_id__isnull=False, has_unsynced_order=False)
    elif filtre == 'non_sync':
        qs = qs.filter(Q(odoo_partner_id__isnull=True) | Q(has_unsynced_order=True))

    paginator = Paginator(qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'clients/liste_clients.html', {
        'clients': page_obj,
        'page_obj': page_obj,
        'q': q,
        'filtre': filtre,
        'total': qs.count(),
        'count_total': count_total,
        'count_sync': count_sync,
        'count_non_sync': count_non_sync,
    })


def creer_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.nom = client.nom.title()
            client.save()

            odoo_id = OdooService().create_partner(client.nom, client.telephone, client.email)
            if odoo_id:
                client.odoo_partner_id = odoo_id
                client.save(update_fields=['odoo_partner_id'])
                messages.success(
                    request,
                    f'Client "{client.nom}" créé et synchronisé avec Odoo (partenaire #{odoo_id}).',
                )
            else:
                logger.error("Odoo — échec de la création du partenaire pour le client id=%s", client.pk)
                messages.warning(
                    request,
                    f'Client "{client.nom}" enregistré localement, mais la synchronisation Odoo a échoué.',
                )

            return redirect('liste_clients')
    else:
        form = ClientForm()
    return render(request, 'clients/creer_client.html', {'form': form})


def resync_client(request, client_id):
    client = get_object_or_404(Client, pk=client_id)
    if client.odoo_partner_id:
        messages.info(request, f'"{client.nom}" est déjà synchronisé avec Odoo (partenaire #{client.odoo_partner_id}).')
        return redirect('liste_clients')

    odoo_id = OdooService().create_partner(client.nom, client.telephone, client.email)
    if odoo_id:
        client.odoo_partner_id = odoo_id
        client.save(update_fields=['odoo_partner_id'])
        messages.success(request, f'"{client.nom}" synchronisé avec Odoo (partenaire #{odoo_id}).')
    else:
        logger.error("Odoo — échec de la resynchronisation pour le client id=%s", client.pk)
        messages.error(request, f'Échec de la synchronisation Odoo pour "{client.nom}". Vérifiez que le service Odoo est accessible.')

    return redirect('liste_clients')


def resync_commandes_client(request, client_id):
    """Synchronise toutes les commandes non-syncées d'un client avec Odoo."""
    client = get_object_or_404(Client, pk=client_id)
    service = OdooService()

    # Si le partenaire lui-même n'est pas encore dans Odoo, on le crée d'abord
    if not client.odoo_partner_id:
        odoo_id = service.create_partner(client.nom, client.telephone, client.email)
        if not odoo_id:
            messages.error(
                request,
                f'Impossible de synchroniser "{client.nom}" : connexion Odoo échouée.',
            )
            return redirect('liste_clients')
        client.odoo_partner_id = odoo_id
        client.save(update_fields=['odoo_partner_id'])

    unsynced = client.orders.filter(odoo_order_id__isnull=True)
    if not unsynced.exists():
        messages.info(request, f'Toutes les commandes de "{client.nom}" sont déjà synchronisées.')
        return redirect('liste_clients')

    ok = err = 0
    for order in unsynced:
        odoo_order_id = service.create_sale_order(
            client.odoo_partner_id,
            order.nom_produit,
            order.prix_total,
            order.quantite,
            order_id=order.pk,
        )
        if odoo_order_id:
            order.odoo_order_id = odoo_order_id
            order.save(update_fields=['odoo_order_id'])
            ok += 1
        else:
            err += 1
            logger.error("Odoo — resync_commandes : échec commande id=%s client id=%s", order.pk, client.pk)

    if err == 0:
        messages.success(request, f'{ok} commande(s) de "{client.nom}" synchronisée(s) avec Odoo.')
    else:
        messages.warning(
            request,
            f'{ok} commande(s) synchronisée(s), {err} échec(s) pour "{client.nom}".',
        )
    return redirect('liste_clients')


def sync_tout(request):
    """Synchronise tous les clients et toutes les commandes non-syncés avec Odoo."""
    if request.method != 'POST':
        return redirect('liste_clients')

    service = OdooService()
    clients_ok = clients_err = orders_ok = orders_err = 0

    # 1 — Clients sans partenaire Odoo
    for client in Client.objects.filter(odoo_partner_id__isnull=True):
        odoo_id = service.create_partner(client.nom, client.telephone, client.email)
        if odoo_id:
            client.odoo_partner_id = odoo_id
            client.save(update_fields=['odoo_partner_id'])
            clients_ok += 1
        else:
            clients_err += 1
            logger.error("Odoo — sync_tout : échec partenaire client id=%s", client.pk)

    # 2 — Commandes sans id Odoo dont le client est maintenant synchronisé
    for order in Order.objects.filter(
        odoo_order_id__isnull=True,
        client__odoo_partner_id__isnull=False,
    ).select_related('client'):
        odoo_order_id = service.create_sale_order(
            order.client.odoo_partner_id,
            order.nom_produit,
            order.prix_total,
            order.quantite,
            order_id=order.pk,
        )
        if odoo_order_id:
            order.odoo_order_id = odoo_order_id
            order.save(update_fields=['odoo_order_id'])
            orders_ok += 1
        else:
            orders_err += 1
            logger.error("Odoo — sync_tout : échec commande id=%s", order.pk)

    parts = []
    if clients_ok:
        parts.append(f'{clients_ok} client(s)')
    if orders_ok:
        parts.append(f'{orders_ok} commande(s)')
    err_parts = []
    if clients_err:
        err_parts.append(f'{clients_err} client(s)')
    if orders_err:
        err_parts.append(f'{orders_err} commande(s)')

    if not parts and not err_parts:
        messages.info(request, 'Tout est déjà synchronisé avec Odoo.')
    elif not err_parts:
        messages.success(request, 'Synchronisation réussie — ' + ', '.join(parts) + '.')
    elif not parts:
        messages.error(request, 'Synchronisation échouée — ' + ', '.join(err_parts) + ' en erreur.')
    else:
        messages.warning(
            request,
            f'Partiellement synchronisé : {", ".join(parts)} OK, {", ".join(err_parts)} en erreur.',
        )
    return redirect('liste_clients')


def creer_commande(request, client_id=None):
    client = get_object_or_404(Client, pk=client_id) if client_id else None
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            order = form.save()
            order_client = order.client

            if order_client.odoo_partner_id:
                odoo_order_id = OdooService().create_sale_order(
                    order_client.odoo_partner_id,
                    order.nom_produit,
                    order.prix_total,
                    order.quantite,
                    order_id=order.pk,
                )
                if odoo_order_id:
                    order.odoo_order_id = odoo_order_id
                    order.save(update_fields=['odoo_order_id'])
                    messages.success(
                        request,
                        f'Commande "{order.nom_produit}" créée et synchronisée avec Odoo (commande #{odoo_order_id}).',
                    )
                else:
                    logger.error(
                        "Odoo — échec de la création de la commande pour order id=%s", order.pk
                    )
                    messages.warning(
                        request,
                        f'Commande "{order.nom_produit}" enregistrée localement, mais la synchronisation Odoo a échoué.',
                    )
            else:
                messages.warning(
                    request,
                    f'Commande "{order.nom_produit}" enregistrée localement. '
                    f'Le client "{order_client.nom}" n\'est pas encore synchronisé avec Odoo.',
                )

            return redirect('liste_clients')
    else:
        initial = {'client': client} if client else {}
        form = OrderForm(initial=initial)
    return render(request, 'clients/creer_commande.html', {'form': form, 'client': client})

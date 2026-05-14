from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_clients, name='liste_clients'),
    path('nouveau/', views.creer_client, name='creer_client'),
    path('commande/nouvelle/', views.creer_commande, name='creer_commande'),
    path('commande/nouvelle/<int:client_id>/', views.creer_commande, name='creer_commande_client'),
    path('<int:client_id>/resync/', views.resync_client, name='resync_client'),
    path('<int:client_id>/resync-commandes/', views.resync_commandes_client, name='resync_commandes_client'),
    path('sync-tout/', views.sync_tout, name='sync_tout'),
]

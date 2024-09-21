from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'),
    path('cliente/<int:pk>/<slug:token>/', views.cliente_start, name='cliente_start'),
    path('cliente/<int:pk>/<slug:token>/<slug:section>/', views.cliente_start, name='cliente_start_section'),
    path('cliente/<int:pk>/<slug:token>/offerta/<int:offerta_id>/', views.cliente_start, name='cliente_start_offerta'),
    path('dati/', views.dati_cliente, name='dati-cliente'),
    path('documenti/', views.documenti_cliente, name='documenti-cliente'),
    path('prodotti/', views.documenti_prodotti, name='documenti_prodotti'),
    path('offerte/', views.offerte_listing, name='offerte'),
    path('offerte/<int:pk>/', views.offerta_view, {'pdf':True}, name='offerta_pdf'),
    path('offerte/<int:pk>/view/', views.offerta_view, name='offerta_view'),
    path('offerte/<int:pk>/presentazione/edit/', views.offerta_presentazione_edit, name='offerta_presentazione_edit'),
    path('offerte/<int:pk>/presentazione/', views.offerta_presentazione, name='offerta_presentazione_pdf'),
    path('offerte/<int:pk>/compilato/<int:compilato_id>/', views.accettazione_offerta, name='accettazione_offerta'),
    path('prodotti/search/', views.prodotti_search, name='cerca_prodotti'),
    path('comuni/search/', views.comuni_search, name='cerca_comuni'),

]
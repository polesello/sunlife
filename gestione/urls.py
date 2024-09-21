from django.urls import path
from . import views
app_name = 'gestione'

urlpatterns = [

    path('', views.index, name='index'),
    path('clienti/', views.clienti, name='clienti'),
    path('clienti/<int:id>/', views.cliente_view, name='cliente_view'),
    path('clienti/<int:id>/edit/', views.cliente_edit, name='cliente_edit'),

    path('clienti/<int:id>/offerte/add/', views.offerta_edit, name='offerta_add'),
    path('clienti/<int:id>/offerte/<int:offerta_id>/', views.offerta_edit, name='offerta_edit'),
    path('clienti/<int:id>/offerte/<int:offerta_id>/delete/', views.offerta_delete, name='offerta_delete'),
    path('clienti/<int:id>/offerte/<int:offerta_id>/copy/', views.offerta_copy, name='offerta_copy'),

    path('clienti/<int:id>/offerte/<int:offerta_id>/copyother/', views.offerta_copy_other, name='offerta_copy_other'),

    path('clienti/<int:id>/offerta_paste/', views.offerta_paste, name='offerta_paste'),
    path('clienti/<int:id>/offerta_cancel_copy/', views.offerta_cancel_copy, name='offerta_cancel_copy'),

]
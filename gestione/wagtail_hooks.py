from django.urls import path, reverse
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from .views import clienti


@hooks.register('register_admin_urls')
def register_clienti_listing_url():
    return [
        path('clienti/', clienti, name='clienti'),
    ]



@hooks.register('register_admin_menu_item')
def register_calendar_menu_item():
    return MenuItem('Clienti', reverse('clienti'), icon_name='user', order=10)
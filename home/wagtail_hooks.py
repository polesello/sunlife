from django.urls import path, reverse
from wagtail.admin.menu import MenuItem
from django.templatetags.static import static
from wagtail import hooks

from wagtail.admin.panels import FieldPanel

from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet, SnippetViewSetGroup
from wagtail.admin.ui.tables import BooleanColumn

from .models import *



class SegnalazioneViewSet(SnippetViewSet):
    model = Segnalazione


class GruppoViewSet(SnippetViewSet):
    model = Gruppo
    list_display = ('nome', 'totale_clienti', BooleanColumn('is_privato', label='Privato'))

class BancaViewSet(SnippetViewSet):
    model = Banca
    list_display = ('nome', 'iban')

class AgenteViewSet(SnippetViewSet):
    model = Agente
    list_display = ('nome', BooleanColumn('attivo'))

class TipoRichiestaViewSet(SnippetViewSet):
    model = TipoRichiesta

class ImpostazioneGeneraleViewSetGroup(SnippetViewSetGroup):
    menu_label = 'Impostazioni generali'
    items = (GruppoViewSet, BancaViewSet, AgenteViewSet, SegnalazioneViewSet, TipoRichiestaViewSet)
register_snippet(ImpostazioneGeneraleViewSetGroup)
 

class DocumentoCompilatoViewSet(SnippetViewSet):
    model = DocumentoCompilato

class DocumentoClienteViewSet(SnippetViewSet):
    model = DocumentoCliente
    list_display = ('cliente', 'nome', 'data_aggiornamento')
register_snippet(DocumentoClienteViewSet)


class ModelloPresentazioneOffertaViewSet(SnippetViewSet):
    model = ModelloPresentazioneOfferta
    search_fields = ('titolo', 'testo',)


class AllegatiViewSetGroup(SnippetViewSetGroup):
    menu_label = 'Allegati'
    items = (DocumentoCompilatoViewSet, ModelloPresentazioneOffertaViewSet)
register_snippet(AllegatiViewSetGroup)

class OffertaViewSet(SnippetViewSet):
    model = Offerta
    list_display = ('titolo', 'cliente', 'data')
    search_fields = ('titolo', 'cliente__ragsoc')
    raw_id_fields = ('cliente',)
    form_view_extra_css = [
        static('home/modeladmin/css/admin.css'),
    ]
    add_to_admin_menu = True
    menu_order = 100
    inspect_view_enabled = True
    actions = ['stampa_offerta']
    form_class = 'vvv'


    # class Media:
    #     js = ("admin/eventparticipant_admin.js",)


register_snippet(Offerta, viewset=OffertaViewSet)

class ClienteViewSet(SnippetViewSet):
    list_display = ('ragsoc', 'citta', 'data', 'gruppo', 'start_url')
    search_fields = ('ragsoc', 'citta', 'indirizzo', 'piva', 'cf', 'telefono', 'email', 'persone__nome', 'persone__telefono')
    list_export = [f.name for f in Cliente._meta.fields]
    list_filter = ('gruppo', 'richieste', 'segnalazione')
    list_per_page = 100
    ordering = ('-data',)
   # add_to_admin_menu = True
    inspect_view_enabled = True
    icon = 'user'
    menu_order = 900
    inspect_template_name = 'home/vedi.html'
#    results_template_name = 'home/cccsmodeladmin/cliente_results.html'


    # def __init__(self, *args, **kwargs):
    #     print('init')
    #     super().__init__(*args, **kwargs)
    #    # self.list_display_links = (None, )
register_snippet(Cliente, viewset=ClienteViewSet)


#print(ClienteViewSet.list_display_links, '++++++++++++++')


class ListinoViewSet(SnippetViewSet):
    model = Listino
    list_display = ('nome', 'marchio', 'totale_prodotti', 'data', BooleanColumn('attivo'))
    search_fields = ('nome',)


class ProdottoViewSet(SnippetViewSet):
    model = Prodotto
    list_display = ('codice', 'descrizione', 'prezzo', BooleanColumn('attivo'), 'listino')


class CatalogoViewSetGroup(SnippetViewSetGroup):
    menu_label = 'Catalogo'
    items = (ListinoViewSet, ProdottoViewSet)
register_snippet(CatalogoViewSetGroup)
 

class VariazioneViewSet(SnippetViewSet):
    model = Variazione
    list_display = ('cliente', 'data')
    search_fields = ('cliente__ragsoc', 'note')
    raw_id_fields = ('cliente',)
    ordering = ('-data',)
    add_to_admin_menu = True
register_snippet(Variazione, viewset=VariazioneViewSet)
  

class DatoClienteViewSet(SnippetViewSet):
    model = DatoCliente
    list_display = ('nome', 'ordine', BooleanColumn('obbligatorio'), BooleanColumn('visibile'))
register_snippet(DatoCliente, viewset=DatoClienteViewSet)


class ComuneViewSet(SnippetViewSet):
    model = Comune
    list_display = ('nome', 'provincia', 'cap')
    search_fields = ('nome',)
    list_filter = ('provincia',)
register_snippet(Comune, viewset=ComuneViewSet)

from .views import admin_importa_cliente, add_listino_1, add_listino_2

@hooks.register('register_admin_urls')
def register_importa_cliente_url():
    return [
        path('importa-cliente/', admin_importa_cliente, name='admin_importa_cliente'),
    ]

@hooks.register('register_admin_urls')
def register_add_listino():
    return [
        path('add-listino/', add_listino_1, name='admin_add_listino_1'),
        path('add-listino/<int:id>/columns/', add_listino_2, name='admin_add_listino_2'),
    ]



@hooks.register('register_admin_menu_item')
def register_importa_cliente():
    return MenuItem('Carica cliente', reverse('admin_importa_cliente'), icon_name='download')


@hooks.register('construct_main_menu')
def hide_page_menu_item(request, menu_items):
    menu_items[:] = [item for item in menu_items if item.name != 'explorer']

@hooks.register('insert_global_admin_js')
def global_admin_js():
    from django.utils.safestring import mark_safe
    return mark_safe(
        '<script src="/static/home/modeladmin/js/choose-presentation.js"></script>',
    )


from wagtail.admin.search import SearchArea

@hooks.register('register_admin_search_area')
def register_frank_search_area():
    return SearchArea('Clienti', '/admin/snippets/home/cliente/', icon_name='user', order=10000)

# from wagtail.admin.ui.components import Component
# from django.utils.safestring import mark_safe

# class WelcomePanel(Component):
#     order = 50

#     def render_html(self, parent_context):
#         from wagtail.templatetags.wagtailcore_tags import render_to_string

#         print(parent_context)
#         print('++++++++++++++++++++++++++++++')
#         print(parent_context.flatten())
#         # transform requestContext into a dict
#         context = parent_context.flatten()

#         return render_to_string('gestione/index.html', context)

# @hooks.register('construct_homepage_panels')
# def add_another_welcome_panel(request, panels):
#     # remove the default welcome panel
#     panels.pop(0)
#     panels.append(WelcomePanel())

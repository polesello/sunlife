# coding=utf-8

from django.shortcuts import render, redirect
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse

from django.contrib.auth import authenticate, login
from django.core.exceptions import ObjectDoesNotExist
from sito.models import *
from django.conf import settings
from django.forms.models import inlineformset_factory
from django.contrib import messages

import os

from django.db.models import Q, Count

from StringIO import StringIO
from django.http import HttpResponse, HttpResponseForbidden
from datetime import datetime
import re



@login_required
def index(request):
    azienda = request.user.azienda_set.first()

    
    if request.user.has_perm('sito.view_all_groups'):
        clienti = Cliente.objects.filter(gruppo__azienda=azienda)
        persone = Persona.objects.filter(cliente__gruppo__azienda=azienda)
        offerte = Offerta.objects.filter(cliente__gruppo__azienda=azienda)
    else:
        clienti = Cliente.objects.filter(gruppo__users = request.user)
        persone = Persona.objects.filter(cliente__gruppo__users = request.user)
        offerte = Offerta.objects.filter(cliente__gruppo__users = request.user)

    prodotti = Prodotto.objects.all()
    
    ultime_offerte = offerte.order_by('-data')[:5]
    ultimi_clienti = clienti.order_by('-data')[:5]

    data = {'clienti':clienti, 'persone':persone, 'offerte':offerte, 'prodotti':prodotti, 'ultime_offerte':ultime_offerte, 'ultimi_clienti':ultimi_clienti}
    return render(request, 'index.html', data)


@login_required
def clienti_listing(request):
    from dateutil.parser import parse as parse_date

    azienda = request.user.azienda_set.first()
    
    if request.user.has_perm('sito.view_all_groups'):
        gruppi = Gruppo.objects.filter(azienda=azienda).order_by('nome')
        clienti = Cliente.objects.filter(gruppo__azienda = azienda)
    else:
        gruppi = Gruppo.objects.filter(users = request.user).order_by('nome')
        clienti = Cliente.objects.filter(users = request.user)


    segnalazioni = Segnalazione.objects.filter(azienda=azienda)

    proprietari = []
    if azienda:
        proprietari = azienda.users.all()
    interventi = TipoRichiesta.objects.all()
    
    gruppo = None
    segnalazione = None
    id_gruppo = request.GET.get('gruppo')
    id_segnalazione = request.GET.get('segnalazione')
    id_intervento = request.GET.get('intervento')
    id_proprietario = request.GET.get('proprietario')
    nome = request.GET.get('nome')
    date_range = request.GET.get('date')
        
    if id_gruppo:
        gruppo = Gruppo.objects.get(pk=id_gruppo)
        clienti = clienti.filter(gruppo__id = id_gruppo)
    
    if id_segnalazione:
        segnalazione = Segnalazione.objects.get(pk=id_segnalazione)
        clienti = clienti.filter(segnalazione__id = id_segnalazione)

    if id_intervento:
        clienti = clienti.filter(richieste__id = id_intervento)

    if id_proprietario:
        clienti = clienti.filter(users__id = id_proprietario)

    if date_range:
        tokens = date_range.split('-')
        if len(tokens) == 2:
            start_date_str, end_date_str = tokens
            start_date = parse_date(start_date_str, dayfirst=True)
            end_date = parse_date(end_date_str, dayfirst=True)
            clienti = clienti.filter(data__gte = start_date, data__lte = end_date)

    if nome:
        clienti = clienti.filter(Q(ragsoc__icontains = nome) | Q(citta__icontains = nome) |
            Q(telefono__icontains = nome) | Q(email__icontains = nome) | Q(persona__nome__icontains = nome) |
            Q(persona__telefono__icontains = nome) | Q(persona__email__icontains = nome)).distinct()

    # TODO pagination
    if not request.GET:
        clienti = clienti[:100]

    return render(request, 'clienti.html', {'clienti':clienti, 'gruppo':gruppo, 'gruppi':gruppi, 'interventi':interventi,'segnalazione':segnalazione, 'segnalazioni':segnalazioni, 'proprietari':proprietari})



@login_required
def clienti_mappa(request):
    azienda = request.user.azienda_set.first()

    gruppo = None
    id_gruppo = request.GET.get('gruppo')

    if request.user.has_perm('sito.view_all_groups'):
        clienti = Cliente.objects.filter(gruppo__azienda = azienda)
    else:
        clienti = Cliente.objects.filter(gruppo__users = request.user)

    
    if id_gruppo:
        gruppo = Gruppo.objects.get(pk=id_gruppo)
        clienti = clienti.filter(gruppo__id = id_gruppo)

    return render(request, 'clienti_mappa.html', {'clienti':clienti, 'gruppo':gruppo})




@login_required
def gruppi_listing(request):
# Controllo che abbia il permesso di vedere tutti i gruppi dell'azienda
# altrimenti solo quelli creati o condivisi con lui
    if request.user.has_perm('sito.view_all_groups'):
        gruppi = Gruppo.objects.filter(visibile=True, azienda__users = request.user)
    else:
        gruppi = Gruppo.objects.filter(visibile=True, users = request.user)

    # Somma i clienti diretti e quelli contenuti nei sottogruppi
    for gruppo in gruppi:
        sottogruppi = gruppo.sottogruppi.filter(visibile=True)
        if not request.user.has_perm('sito.view_all_groups'):
            sottogruppi = sottogruppi.filter(users = request.user)
        gruppo.n_clienti = gruppo.cliente_set.count() + sottogruppi.aggregate(totale=Count('cliente'))['totale']


    payload = {'gruppi':gruppi}
    return render(request, 'gruppi_listing.html', payload)



@login_required
@permission_required('sito.change_gruppo')
def gruppo_edit(request, id=None):
    azienda = request.user.azienda_set.first()

    cancel_link = reverse('gruppi_listing')
    if id:
        gruppo = Gruppo.objects.get(pk=id)
    else:
        gruppo = Gruppo(azienda=azienda)
    form = GruppoForm(instance=gruppo)
    
    if request.method == 'POST':
        if request.POST.get('action') == 'delete':
            gruppo.delete()
            messages.success(request, "Gruppo eliminato.")
            return redirect('gruppi_listing')
        
        form = GruppoForm(request.POST, request.FILES, instance=gruppo)
        if form.is_valid():
            gruppo = form.save()
            gruppo.users.add(request.user)
            if not request.user.is_staff:
                azienda = Azienda.objects.filter(users=request.user).first()
                if azienda:
                    gruppo.azienda = azienda
                    gruppo.save()
            return redirect(reverse('gruppi_listing'))
    payload = {'form':form, 'cancel_link':cancel_link}
    return render(request, 'edit.html', payload)


@permission_required('sito.delete_gruppo')
def gruppo_delete(request, id):
    gruppo = Gruppo.objects.get(pk=id)
    if request.method == 'POST':
        gruppo.delete()
    return redirect(reverse('gruppi_listing'))
    





@login_required
def condizioni_gruppo(request, gruppo_id):
    gruppo = Gruppo.objects.get(pk=gruppo_id)
    marchi = Marchio.objects.all()

    # Salvataggio condizioni del marchio
    for key, value in request.POST.iteritems():
    
# Condizioni standard, generali per un marchio
        if key.startswith('cond-'):
            tokens = key.split('-')
            if len(tokens) == 3:
                dummy, cond_marchio_id, cond_gruppo_id = tokens
                condizione_gruppo_valore = None
                if cond_gruppo_id:
                    condizione_gruppo = CondizioneGruppo.objects.get(pk=cond_gruppo_id)
                else:
                    condizione_marchio = CondizioneMarchio.objects.get(pk=cond_marchio_id)
                    condizione_gruppo = CondizioneGruppo(gruppo=gruppo, condizione=condizione_marchio)
                
                value = value.strip()
                if value:
                    if not cond_gruppo_id and value != condizione_marchio.valore.strip() or cond_gruppo_id:
                        condizione_gruppo.valore = value
                        condizione_gruppo.save()
                elif cond_gruppo_id:
                    condizione_gruppo.delete()
                    
                    
# Aggiungo la lista "condizioni" ad ogni marchio, con il valore specifico del gruppo, se c'è,
# altrimenti quello di default impostato nelle condizioni dei marchi
    for marchio in marchi:
        condizioni = []
        condizioni_marchio = marchio.condizionemarchio_set.all()
        for condizione_marchio in condizioni_marchio:
            condizione_gruppo = CondizioneGruppo.objects.filter(condizione=condizione_marchio, gruppo=gruppo).first()
            if condizione_gruppo:
                condizione_nome = condizione_gruppo.condizione.nome
                condizione_valore = condizione_gruppo.valore
            else:
                condizione_nome = condizione_marchio.nome
                condizione_valore = condizione_marchio.valore            
            condizioni.append({'nome':condizione_nome, 'valore':condizione_valore, 'condizione_marchio_id':condizione_marchio.id, 'condizione_gruppo_id':condizione_gruppo and condizione_gruppo.id or '', 'is_gruppo':condizione_gruppo})

        marchio.condizioni = condizioni
            
            
    payload = {'gruppo':gruppo, 'marchi':marchi}
    return render(request, 'condizioni_gruppo.html', payload)




@permission_required('sito.change_cliente')
def excel_export(request):
    import xlwt
# Larghezza colonne (in unità di misura sconosciute)
    COL_WIDTHS = [30, 30, 7, 25, 4, 15, 15, 20, 15, 15, 20, 30, 15, 15, 30]
    cliente_model = Cliente()

    response = HttpResponse(mimetype="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=aziende.xls'

    wb = xlwt.Workbook()
        
    gruppi = Gruppo.objects.all()
    for gruppo in gruppi:
# Al massimo 31 caratteri nei nomi dei fogli
# https://mvp-apps.sourcerepo.com/redmine/mvp/issues/1185
        sheet_name = gruppo.nome[:31].replace('/', '-')
        ws = wb.add_sheet(sheet_name)
    
    # Intestazione
        title_style = xlwt.easyxf('font: height 320, name Arial, bold on; align: horiz center')
        bold_style = xlwt.easyxf('font: bold on')

        fields = cliente_model._meta.fields
        exclude = ['id', 'gruppo', 'stato']    
        fields = [f for f in fields if f.name not in exclude]

        for i, field in enumerate(fields):
            if i < len(COL_WIDTHS):
                ws.col(i).width = 256 * COL_WIDTHS[i]
            ws.write(0, i, unicode(field.verbose_name, 'utf-8'), title_style)
        
        aziende = Cliente.objects.filter(gruppo=gruppo)
        
        row = 1
        for cliente in aziende:
            for j, field in enumerate(fields):
                value = getattr(cliente, field.name, '')
                if j:
                    ws.write(row, j, value)
                else:
                    ws.write(row, j, value, bold_style)
            row += 1
            persone = Persona.objects.filter(cliente=cliente)
            for persona in persone:
                ws.write(row, 0, persona.nome)
                ws.write(row, 1, persona.mansione)
                ws.write(row, 5, persona.telefono)
                ws.write(row, 7, persona.email)
                row += 1
# Riga vuota dopo ogni cliente
            row += 1


    wb.save(response)
    return response    
    
    
    
    
#    return HttpResponse(output.read(), mimetype='application/ms-excel')


    
@login_required
def cliente_view(request, cliente_id, as_pdf=False):
# Solo il cliente e l'amministratore possono vederla
    azienda = request.user.azienda_set.first()

    cliente = Cliente.objects.get(pk=cliente_id)

    if not(request.user.has_perm('sito.view_all_groups') and cliente.gruppo and cliente.gruppo.azienda == azienda
        or not request.user.has_perm('sito.view_all_groups') and request.user in cliente.gruppo.users.all()):
            return redirect(reverse('gruppi_listing'))

    
    
    
#    if not request.user.has_perm('sito.change_cliente') and not request.user.username == cliente.email and not as_pdf:
#        return HttpResponseForbidden("Non puoi visualizzare questa pagina.")
    
#
# Tutte le condizioni disponibili
#
    marchi = Marchio.objects.all()
    for marchio in marchi:
        condizioni = []
        condizionedata = CondizioneData.objects.filter(cliente=cliente, marchio=marchio)
        if condizionedata:
            condizionedata = condizionedata[0]
        marchio.condizionedata = condizionedata
        
        valutazione = ValutazioneCliente.objects.filter(cliente=cliente, marchio=marchio)
        if valutazione:
            marchio.valutazione = valutazione[0].valore
        else:
            marchio.valutazione = 0
        
        condizioni_marchio = marchio.condizionemarchio_set.all()

        for condizione_marchio in condizioni_marchio:
            condizioni_cliente = CondizioneCliente.objects.filter(cliente=cliente, condizione = condizione_marchio)
            condizioni_gruppo = CondizioneGruppo.objects.filter(gruppo=cliente.gruppo, condizione = condizione_marchio)

            is_gruppo = True
            valore = condizione_marchio.valore
            is_empty = False
            condizione_cliente = None
            if condizioni_cliente:
                condizione_cliente = condizioni_cliente[0]
                valore = condizione_cliente.valore
                is_gruppo = False

            elif condizioni_gruppo:
                valore = condizioni_gruppo[0].valore
                is_empty = True
            else:
                is_empty = True

            condizione = {'condizione_cliente':condizione_cliente, 'condizione_marchio':condizione_marchio, 'nome':condizione_marchio.nome, 'valore':valore, 'is_gruppo':is_gruppo, 'is_empty':is_empty, 'is_special':False}
            condizioni.append(condizione)

        condizioni_particolari = CondizioneParticolareCliente.objects.filter(cliente=cliente, marchio=marchio)
        for c in condizioni_particolari:
            condizione = {'condizione_cliente':c, 'condizione_marchio':None, 'nome':c.nome, 'valore':c.valore, 'is_gruppo':False, 'is_empty':False, 'is_special':True}
            condizioni.append(condizione)

        marchio.condizioni = condizioni

# Solo per i progettisti, aggiungo le visite:
        if cliente.gruppo and cliente.gruppo.is_progettista:
            visite = CondizioneData.objects.filter(cliente=cliente, marchio=marchio)
            marchio.visite = visite

# Persona vuota per mostrare il form di aggiunta
#    persone = Persona.objects.filter(cliente=cliente)
#    persona = Persona(cliente=cliente)
#    persone = list(persone)
#    persone.append(persona)


# Formset per le persone
    PersonaFormSet = inlineformset_factory(Cliente, Persona, form=PersonaForm)
    persone_formset = PersonaFormSet(instance=cliente)

    if request.method == 'POST' and 'persona_set-TOTAL_FORMS' in request.POST:
        persone_formset = PersonaFormSet(request.POST, instance=cliente)
        if persone_formset.is_valid():
            persone_formset.save()


            
# Formset per le attività
    AttivitaFormSet = inlineformset_factory(Cliente, Attivita, form=AttivitaForm)
    attivita_initial = [{'data': date.today()} for _ in range(AttivitaFormSet.extra)]
    attivita_formset = AttivitaFormSet(instance=cliente, initial=attivita_initial)

    if request.method == 'POST' and 'attivita-TOTAL_FORMS' in request.POST:
        attivita_formset = AttivitaFormSet(request.POST, instance=cliente, initial=attivita_initial)

        if attivita_formset.is_valid():
            attivita_formset.save()
            return redirect(cliente)
        else:
            print "TUTTO UN CASINO"
            print attivita_formset.errors

    documenti = DocumentoCliente.objects.filter(cliente=cliente)
    cartelle = CartellaDocumenti.objects.filter(cliente=cliente)
    if not request.user.is_staff:
        documenti = documenti.exclude(privato=True)
		
    offerte = Offerta.objects.filter(cliente=cliente)

# Eventuale offerta da copiare da un altro cliente, messa negli appunti
    offerta_id_copied = request.session.get('offerta_id_copied')
    offerta_copied = None
    if offerta_id_copied:
        # 1.2.2021 - Nel caso l'avesse già cancellata
        try:
            offerta_copied = Offerta.objects.get(pk=offerta_id_copied)
        except:
            pass
 
    payload = {'cliente': cliente, 'documenti':documenti, 'cartelle':cartelle, 'offerte':offerte, 'offerta_copied':offerta_copied, 'marchi':marchi, 'persone_formset':persone_formset, 'attivita_formset':attivita_formset}
    if as_pdf:
        return payload
    return render(request, 'cliente.html', payload)
            


@permission_required('sito.change_cliente')
def cliente_valutazione(request, cliente_id):
# Assegna le stelline all'cliente per un certo marchio
    cliente = Cliente.objects.get(pk=cliente_id)
    marchio_id = request.GET.get('marchio')
    valore = request.GET.get('valore')
    try:
        marchio_id = int(marchio_id)
        valore = int(valore)
    except:
        marchio_id = 0
        valore = 0
        
    marchio = Marchio.objects.get(pk=marchio_id)
    if marchio:
        try:
            valutazione = ValutazioneCliente.objects.get(cliente=cliente, marchio=marchio)
            valutazione.valore = valore
        except ObjectDoesNotExist:
            valutazione = ValutazioneCliente(cliente=cliente, marchio=marchio, valore=valore)
        if valore:
            valutazione.save()
        else:
            valutazione.delete()
    
    return redirect(cliente)



#
# Cambio link per generazione pdf
#
def fetch_resources(uri, rel):
#    path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))

    path = uri.replace('/static/', '/home/nello/sunlife/static/').replace('/media/', '/home/nello/sunlife/sunlife/media/')


    return path
      

@login_required
def cliente_pdf(request, cliente_id):
    from subprocess import Popen, PIPE, STDOUT    
    import os
    
    cliente = Cliente.objects.get(pk=cliente_id)
    
    url = 'https://my.sunlifegroup.it/cliente/%s/table' % cliente_id
    filename = '/tmp/cliente-%s.pdf' % cliente_id
    cmd = '/home/nello/wkhtmltopdf.sh %s %s' % (url, filename)
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    debug = p.stdout.read()    
    pdf_file = open(filename)
    pdf_content = pdf_file.read()
    pdf_file.close()
    os.remove(filename)
    
    response = HttpResponse(pdf_content, mimetype='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=%s.pdf' % slugify(cliente.ragsoc)
    return response




# Vista alternativa usando tabelle, per poi esportare in pdf
def cliente_table(request, cliente_id):
    payload = {}
# La mostro solo se sono autenticato oppure viene chiamata dallo stesso server (per generare il pdf)
    if request.user.is_authenticated() or request.META['REMOTE_ADDR'] == '217.194.13.218':
        payload = cliente_view(request, cliente_id, as_pdf = True)
    return render(request, 'cliente_table.html', payload)




@login_required
@permission_required('sito.change_cliente')
def cliente_edit(request, cliente_id=None):
    azienda = request.user.azienda_set.first()

    if cliente_id:
        cliente = Cliente.objects.get(pk=cliente_id)
        cancel_link = cliente.get_absolute_url()
    else:
        cliente = Cliente()
        gruppo_id = request.GET.get('gruppo')
        if gruppo_id:
            gruppo = Gruppo.objects.get(pk=gruppo_id)
            cliente.gruppo = gruppo
        cancel_link = reverse('clienti_listing')

# Se cliente privato usa un form ridotto
    EditForm = ClienteForm
    if cliente.gruppo and cliente.gruppo.is_privato:
        EditForm = ClientePrivatoForm
        
    initial = not cliente.pk and {'users':[request.user]} or None
    form = EditForm(azienda, instance=cliente, user=request.user, initial=initial)


    if request.method == 'POST':
        if request.POST.get('action') == 'delete' and request.user.has_perm('sito.delete_cliente'):
            cliente.delete()
            if cliente.gruppo:
                return redirect(reverse('clienti_listing') + '?gruppo=%s' % cliente.gruppo.id)
            else:
                return redirect(reverse('clienti_listing'))
    
    
        form = EditForm(azienda, request.POST, request.FILES, instance=cliente, user=request.user)
        if form.is_valid():
        
            cliente = form.save()
# Ottengo le coordinate dalle API di Google
            try:
                coords = cliente.geoRefCliente()
                if coords:
                    cliente.lat = coords['lat']
                    cliente.lng = coords['lng']
                else:
                    cliente.lat = None
                    cliente.lng = None
            except:
                pass
            
            cliente.save()
            messages.success(request, 'Cliente salvato')

            return redirect(cliente)
    
    return render(request, 'edit.html', {'form':form, 'cancel_link': cancel_link})


@login_required
@permission_required('sito.change_cliente')
def cliente_info_edit(request, cliente_id=None):
    import json

    cliente = Cliente.objects.get(pk=cliente_id)
    cancel_link = cliente.get_absolute_url()

    form = ClienteInfoForm(request.POST or None, initial=cliente.altri_dati_raw)
    fields = DatoCliente.objects.filter(visibile=True)
    for field in fields:
        if field.tipo == 'N':
            form.fields[field.codice] = forms.IntegerField()#widget=TextInput(attrs={'type':'number'}))
        elif field.tipo == 'T':
            form.fields[field.codice] = forms.TextField()
        elif field.tipo == 'B':
            form.fields[field.codice] = forms.BooleanField()
        elif field.tipo == 'D':
            print "AIUTO, una data"
            form.fields[field.codice] = forms.DateField(widget=DateWidget())
        else:
            form.fields[field.codice] = forms.CharField()

        form.fields[field.codice].label = field.nome
        form.fields[field.codice].required = field.obbligatorio

    if request.method == 'POST':
        if form.is_valid():
            # coversione date
            data_copy = form.cleaned_data.copy()
            for k, v in data_copy.items():
                if isinstance(v, date):
                    data_copy[k] = v.strftime('%d-%m-%Y')

            altri_dati = json.dumps(data_copy)
            cliente.altro = altri_dati
            cliente.save()
            return redirect(cancel_link)

    return render(request, 'info_edit.html', {'form':form, 'cliente':cliente, 'cancel_link': cancel_link})



@login_required
def file_upload(request, cliente_id):
    IMAGE_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/gif')

    cliente = Cliente.objects.get(pk=cliente_id)
    
    uploads = []
    if request.FILES.get("file"):
        for f in request.FILES.getlist("file"):
            doc_page = DocumentoCliente(cliente=cliente, file_obj=f, nome=f.name)
# Se è un'immagine controllo che lo sia veramente, altrimenti potrebbero trascinare dei file pdf nell'area immagini:
#            if f.content_type not in IMAGE_CONTENT_TYPES:
#                pass

            # 20.11.2020 - rinomino jfif in jpg
            filename = f.name
            if filename.endswith('.jfif'):
                filename = filename[:-4] + 'jpg'
                doc_page.nome = filename
            doc_page.save()

            if filename.endswith('.jfif'):
                import os
                os.rename(doc_page.file.path, doc_page.file.path.replace('.jfif', '.jpg'))
            
    
    return redirect(cliente)



@login_required
@permission_required('sito.change_cliente')
@csrf_exempt
def cliente_sort_persone(request, cliente_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    id_persone = request.POST.getlist('id')
    for i, id_persona in enumerate(id_persone):
        try:
            persona = Persona.objects.get(pk=id_persona)
            persona.ordine = i
            persona.save()
        except ObjectDoesNotExist:
            pass
    if request.is_ajax():
        return HttpResponse('OK')
    else:
        return redirect(cliente)



@login_required
@permission_required('sito.change_documentocliente')
def documento_edit(request, cliente_id, documento_id=None):
    cliente = Cliente.objects.get(pk=cliente_id)
    if documento_id:
        documento = DocumentoCliente.objects.get(pk=documento_id)
    else:
        documento = DocumentoCliente(cliente=cliente)
    form = DocumentoClienteForm(instance=documento)
    
    if request.method == 'POST':
        form = DocumentoClienteForm(request.POST, request.FILES, instance=documento)
        if form.is_valid():
            documento = form.save()
            if not documento.nome:
                documento.nome = os.path.basename(documento.file.name).replace("_"," ").replace("-"," ")
                documento.save()
            if request.is_ajax():
                return render(request, 'document-single.html', {'cliente':cliente, 'doc': documento, 'form':form})        
            else:
                return redirect(cliente)
        else:
            return HttpResponse(str(form))        
    
    
    return render(request, 'edit.html', {'documento': documento, 'form':form})


@login_required
@permission_required('sito.delete_documentocliente')
@csrf_exempt
def documento_delete(request, cliente_id, documento_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    documento = DocumentoCliente.objects.get(pk=documento_id)
    if request.method == 'POST':
    	documento.delete()
        if request.is_ajax():
            return HttpResponse('OK') 
    return redirect(cliente)



@staff_member_required
def documento_change_state(request, cliente_id, documento_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    documento = DocumentoCliente.objects.get(pk=documento_id)
    documento.privato = not documento.privato
    documento.save()

    return redirect(cliente)


@permission_required('sito.delete_documentocliente')
def documento_rename_jfif(request, cliente_id, documento_id):
    import os

    cliente = Cliente.objects.get(pk=cliente_id)
    documento = DocumentoCliente.objects.get(pk=documento_id)
    
    if documento.file.name.lower().endswith('.jfif'):
        os.rename(documento.file.path, documento.file.path[:-4] + 'jpg')
        documento.file.name = documento.file.name[:-4] + 'jpg'
        if documento.nome.lower().endswith('.jfif'):
            documento.nome = documento.nome[:-4] + 'jpg'

        documento.save()

    return redirect(cliente)


@login_required
def condizionecliente_edit(request, cliente_id, condizione_marchio_id, condizione_id=None):
    cliente = Cliente.objects.get(pk=cliente_id)
    condizione_marchio = CondizioneMarchio.objects.get(pk=condizione_marchio_id)

    if condizione_id:
        condizione = CondizioneCliente.objects.get(pk=condizione_id)
    else:
        condizione = CondizioneCliente(cliente=cliente, condizione=condizione_marchio)
    form = CondizioneClienteForm(instance=condizione)
    
    if request.method == 'POST':
        form = CondizioneClienteForm(request.POST, instance=condizione)
        if form.is_valid():
        
# Se inserisco un valore vuoto, elimino la condizione
            if condizione_id and not form.cleaned_data['valore'].strip():
                condizione.delete()
            else:
                form.save()
            
# Aggiorno la data di aggiornamento
            data_condizione = CondizioneData.objects.filter(cliente=cliente, marchio=condizione.condizione.marchio)
            
            if data_condizione:
                data_condizione = data_condizione[0]
            else:
                data_condizione = CondizioneData(cliente=cliente, marchio=condizione.condizione.marchio)
            data_condizione.data = datetime.now()
            data_condizione.save()

                
            return redirect(cliente)
    
    return render(request, 'condizionecliente_edit.html',
            {'condizione': condizione, 'condizione_marchio': condizione_marchio, 'form':form})


@login_required
@permission_required('sito.delete_condizionecliente')
def condizionecliente_delete(request, cliente_id, condizione_marchio_id, condizione_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    condizione = CondizioneCliente.objects.get(pk=condizione_id)
    condizione.delete()
    return redirect(cliente) 


@login_required
@permission_required('sito.change_condizioneparticolarecliente')
def condizioneparticolarecliente_edit(request, cliente_id, marchio_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    marchio = Marchio.objects.get(pk=marchio_id)
    condizione = CondizioneParticolareCliente(cliente=cliente, marchio=marchio)
    form = CondizioneParticolareClienteForm(instance=condizione)
    
    if request.method == 'POST':
        form = CondizioneParticolareClienteForm(request.POST, instance=condizione)
        if form.is_valid():
            form.save()
            return redirect(cliente)
    
    return render(request, 'condizioneparticolarecliente_edit.html',
            {'condizione': condizione, 'form':form})



@login_required
@permission_required('sito.change_condizionecliente')
def condizioni_save(request, cliente_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    for key, value in request.POST.iteritems():
    
# Condizioni standard, generali per un marchio
        if key.startswith('cond-'):
            tokens = key.split('-')
            if len(tokens) == 3:
                dummy, cond_marchio_id, cond_cliente_id = tokens
                condizione_gruppo_valore = None
                if cond_cliente_id:
                    condizione_cliente = CondizioneCliente.objects.get(pk=cond_cliente_id)
                else:
                    condizione_marchio = CondizioneMarchio.objects.get(pk=cond_marchio_id)
                    condizione_cliente = CondizioneCliente(cliente=cliente, condizione=condizione_marchio)
                    condizione_gruppo = CondizioneGruppo.objects.filter(condizione=condizione_marchio, gruppo = cliente.gruppo)
                    if condizione_gruppo:
                        condizione_gruppo_valore = condizione_gruppo[0].valore

                if value.strip() and value.strip() not in (condizione_cliente.valore, condizione_gruppo_valore):
                    condizione_cliente.valore = value
                    condizione_cliente.save()

##
## TODO: Si può uniformare il salvataggio della data di aggiornamento?
##


# Aggiorno la data di aggiornamento
                    marchio = condizione_cliente.condizione.marchio
                    data_condizione = CondizioneData.objects.filter(cliente=cliente, marchio=marchio)
                    if data_condizione:
                        data_condizione = data_condizione[0]
                    else:
                        data_condizione = CondizioneData(cliente=cliente, marchio=marchio)
                    data_condizione.data = datetime.now()
                    data_condizione.save()
   
                elif not value.strip() and condizione_cliente.id:
                    condizione_cliente.delete()

# Condizioni speciali per un determinato cliente
        if key.startswith('spec-'):
            tokens = key.split('-')
            if len(tokens) == 2:
                dummy, cond_cliente_id = tokens
                condizione_particolare_cliente = CondizioneParticolareCliente.objects.get(pk=cond_cliente_id)

# Salvo e aggiorno la data solo se ho cambiato le condizioni rispetto a quelle già salvate
                if value.strip() and value != condizione_particolare_cliente.valore:
                    condizione_particolare_cliente.valore = value
                    condizione_particolare_cliente.save()
                    
# Aggiorno la data di aggiornamento
                    marchio = condizione_cliente.condizione.marchio
                    data_condizione = CondizioneData.objects.filter(cliente=cliente, marchio=marchio)
                    if data_condizione:
                        data_condizione = data_condizione[0]
                    else:
                        data_condizione = CondizioneData(cliente=cliente, marchio=marchio)
                    data_condizione.data = datetime.now()
                    data_condizione.save()
   
                elif not value.strip():
                    condizione_particolare_cliente.delete()




    return redirect(cliente) 


@login_required
@permission_required('sito.change_condizionedata')
def condizionedata_edit(request, cliente_id, marchio_id, condizione_id):
    condizionedata = CondizioneData.objects.get(pk=condizione_id)
    cliente = condizionedata.cliente

    form = CondizioneDataForm(instance=condizionedata)
    
    if request.method == 'POST':
        form = CondizioneDataForm(request.POST, instance=condizionedata)
        if form.is_valid():
            form.save()    
            return redirect(cliente)
    
    return render(request, 'condizionedata_edit.html',
            {'condizionedata': condizionedata, 'form':form})
 
 
@login_required
@permission_required('sito.change_condizionedata')
def condizionedata_add(request, cliente_id, marchio_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    marchio = Marchio.objects.get(pk=marchio_id)  
    condizionedata = CondizioneData(cliente=cliente, marchio=marchio)
    form = CondizioneDataForm(instance=condizionedata)
    
    if request.method == 'POST':
        form = CondizioneDataForm(request.POST, instance=condizionedata)
        if form.is_valid():
            try:
                form.save()
                return redirect(cliente)
            except:
                pass        

    
    return render(request, 'condizionedata_edit.html',
            {'condizionedata': condizionedata, 'form':form}) 
 
 
@login_required
@permission_required('sito.delete_condizionedata')
def condizionedata_delete(request, cliente_id, marchio_id, condizione_id):
    condizionedata = CondizioneData.objects.get(pk=condizione_id)
    cliente = condizionedata.cliente
    
    if request.method == 'POST':
        condizionedata.delete()
   
    return redirect(cliente)
    
    
    
@login_required
@permission_required('sito.change_condizionegruppo')
def condizionigruppi_edit(request, gruppo_id=None):
    gruppi = Gruppo.objects.all()
    gruppo = None
    marchi = Marchio.objects.all()
    col_width = marchi and 100 / len(marchi) or 0;    
    
    if gruppo_id:
        gruppo = Gruppo.objects.get(pk=gruppo_id)


# Salvataggio nuove condizioni
        if request.method == 'POST':
            for key, value in request.POST.iteritems():            
                if key.startswith('cond-'):
                    tokens = key.split('-')
                    if len(tokens) == 3:
                        dummy, cond_marchio_id, cond_gruppo_id = tokens
                        if cond_gruppo_id:
                            condizione_gruppo = CondizioneGruppo.objects.get(pk=cond_gruppo_id)
                        else:
                            condizione_marchio = CondizioneMarchio.objects.get(pk=cond_marchio_id)
                            condizione_gruppo = CondizioneGruppo(gruppo=gruppo, condizione=condizione_marchio)
        
                        if value.strip() and value != condizione_gruppo.valore:
                            condizione_gruppo.valore = value
                            condizione_gruppo.save()
                        if not value.strip() and cond_gruppo_id:
                            condizione_gruppo.delete()


        for marchio in marchi:
            condizioni = []
            condizioni_marchio = marchio.condizionemarchio_set.all()
        
            for condizione_marchio in condizioni_marchio:
                condizione = {'condizione_marchio':condizione_marchio, 'condizione_gruppo':None, 'valore':''}
            
                condizioni_gruppo = CondizioneGruppo.objects.filter(gruppo=gruppo, condizione = condizione_marchio)
                if condizioni_gruppo:
                    condizione_gruppo = condizioni_gruppo[0]
                    condizione['condizione_gruppo'] = condizione_gruppo
                    condizione['valore'] = condizione_gruppo.valore
                
                condizioni.append(condizione)
                
            marchio.condizioni = condizioni



    return render(request, 'condizionigruppi.html',
            {'gruppi': gruppi, 'gruppo_sel':gruppo, 'marchi':marchi, 'col_width':col_width})
 

    
@permission_required('sito.change_condizionemarchio')
def condizioni_listing(request):
    """Mostra le possibili condizioni disponibili per un certo marchio"""
    condizioni = CondizioneMarchio.objects.all()
    payload = {'condizioni': condizioni}
    return render(request, 'condizioni_listing.html', payload)
                  
                  
    

#@permission_required(lambda u: u.is_superuser)
@permission_required('sito.change_newsletter')
def newsletter_listing(request):

# Rimozione allegato
    remove_id = request.GET.get('remove')
    if remove_id:
        try:
            newsletter_to_remove = Newsletter.objects.get(pk=remove_id)
            if request.GET.get('delete') == 'DELETE':
                newsletter_to_remove.delete()
                return redirect(request.path)
        except ObjectDoesNotExist:
            pass

    newsletters = Newsletter.objects.all()
    payload = {'newsletters':newsletters}
    return render(request, 'newsletter_listing.html', payload)


@permission_required('sito.delete_newsletter')
def newsletter_delete(request, id):
    newsletter = Newsletter.objects.get(pk=id)
    if request.method == 'POST':
        newsletter.delete()
    return redirect(reverse('newsletter_listing'))
    


@permission_required('sito.change_newsletter')
def newsletter_edit(request, id=None):
    newsletter = Newsletter(mittente_nome=request.user.get_full_name())
    if id:
        newsletter = Newsletter.objects.get(pk=id)
    newsletterform = NewsletterForm(instance=newsletter)
    allegatoform = AllegatoNewsletterForm()
    cancel_link = reverse('newsletter_listing')

# Salvataggio o aggiunta allegati
    if request.method == 'POST':
        newsletterform = NewsletterForm(request.POST, instance=newsletter)
        if newsletterform.is_valid():
            newsletterform.save()
            return redirect(newsletterform.instance)

        if request.POST.get('addfile'):
            allegato = AllegatoNewsletter(newsletter=newsletter)
            allegatoform = AllegatoNewsletterForm(request.POST, request.FILES, instance=allegato)
            if allegatoform.is_valid():
                allegatoform.save()
                return redirect(request.path)

# Rimozione allegato
    allegato_id = request.GET.get('remove')
    if allegato_id:
        try:
            allegato_to_remove = AllegatoNewsletter.objects.get(pk=allegato_id)
            allegato_to_remove.delete()
        except ObjectDoesNotExist:
            pass
           
    payload = {'newsletter':newsletter, 'newsletterform':newsletterform, 'allegatoform':allegatoform, 'cancel_link':cancel_link}
    return render(request, 'newsletter_edit.html', payload)


@permission_required('sito.change_newsletter')
def newsletter_destinatari(request, id):
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError
        
    newsletter = Newsletter.objects.get(pk=id)
    gruppi = Gruppo.objects.all()

    aziende = []
    aziende_id = []
    province = []

# Carico le aziende di un gruppo
    if request.method == 'POST':
        if request.POST.get('select_gruppo'):
            gruppo_id = request.POST.get('gruppo')
            if gruppo_id:
                aziende = Cliente.objects.filter(gruppo__id = gruppo_id) #.exclude(email = '')
                province = list(set([a.provincia.upper() for a in aziende]))
                province.sort()
    
        if request.POST.get('select_provincia'):
            gruppo_id = request.POST.get('gruppo')
            provincia = request.POST.get('provincia')
            if gruppo_id:
                aziende_gruppo = Cliente.objects.filter(gruppo__id = gruppo_id) #.exclude(email = '')
                province = list(set([a.provincia.upper() for a in aziende_gruppo]))
                province.sort()
            if provincia:
                aziende = Cliente.objects.filter(gruppo__id = gruppo_id, provincia = provincia)
            else:
                aziende = aziende_gruppo

        if request.POST.get('delete_all'):
            emails = DestinatarioNewsletter.objects.filter(newsletter=newsletter)
            emails.delete()
            return redirect(newsletter.get_absolute_url() + '/destinatari')

# Salvo i destinatari aggiunti
        if request.POST.get('add'):
            emails = request.POST.get('emails')
            if emails:
                emails = re.split('[;,\s]+', emails)
                for email in emails:
                    exists = DestinatarioNewsletter.objects.filter(newsletter=newsletter, email=email)
                    if not exists:
                        try:
                            validate_email(email)
                            d = DestinatarioNewsletter(newsletter=newsletter, email=email)
                            d.save() 
                        except ValidationError:
                            pass
        
            ids = request.POST.getlist('cliente')
            destinatari = Cliente.objects.filter(pk__in = ids).exclude(email = '')
            
            for destinatario in destinatari:
                d, created = DestinatarioNewsletter.objects.get_or_create(newsletter=newsletter, cliente=destinatario)
#                if not exists:
#                    d = DestinatarioNewsletter(newsletter=newsletter, cliente=destinatario)
#                    d.save()
            
            ids = request.POST.getlist('persona')
            destinatari = Persona.objects.filter(pk__in = ids).exclude(email = '')
            for destinatario in destinatari:
                d, created = DestinatarioNewsletter.objects.get_or_create(newsletter=newsletter, persona=destinatario)
#                if not exists:
#                    d = DestinatarioNewsletter(newsletter=newsletter, persona=destinatario)
#                    d.save()
#                    
# Rimozione singolo destinatario
    email_to_remove = request.GET.get('remove')
    if email_to_remove:
        if '<' in email_to_remove and '>' in email_to_remove:
            email_to_remove = email_to_remove[email_to_remove.find('<') + 1 : email_to_remove.find('>')].strip()
            
        d_to_remove = DestinatarioNewsletter.objects.filter(Q(persona__email = email_to_remove) | Q(cliente__email = email_to_remove) | Q(email = email_to_remove))
        d_to_remove.delete()


    destinatari = DestinatarioNewsletter.objects.filter(newsletter=newsletter)
    emails = []
    aziende_ids = [d.cliente.id for d in destinatari if d.cliente]
    persone_ids = [d.persona.id for d in destinatari if d.persona]


    emails_link = 'mailto:%s?bcc=' % request.user.email

    for d in destinatari:
        email = None
        if d.email:
            email = d.email
            emails_link += d.email + ';'
        elif d.cliente and d.cliente.email:
            email = '%s <%s>' % (d.cliente.ragsoc, d.cliente.email)
            emails_link += d.cliente.email + ';'
        elif d.persona and d.persona.email:
            email = '%s <%s>' % (d.persona.nome, d.persona.email)
            emails_link += d.persona.email + ';'
        if email:
            emails.append(email)
            
    #DEBUG
    # destinatari = []
            
    payload = {'newsletter':newsletter, 'gruppi':gruppi, 'province':province, 'aziende':aziende, 'destinatari':destinatari, 'aziende_ids':aziende_ids, 'persone_ids':persone_ids, 'emails':emails, 'emails_link':emails_link}
    return render(request, 'newsletter_destinatari.html', payload)


@permission_required('sito.change_newsletter')
def newsletter_preview(request, id):
    newsletter = Newsletter.objects.get(pk=id)
    
    emails = []
    for d in newsletter.destinatari.all():
        email = None
        if d.email:
            email = d.email
        elif d.cliente and d.cliente.email:
            email = '%s <%s>' % (d.cliente.ragsoc, d.cliente.email)
        elif d.persona and d.persona.email:
            email = '%s <%s>' % (d.persona.nome, d.persona.email)
        if email:
            emails.append(email)
            
    if newsletter.link_allegati:
        newsletter.add_linked_files(request)

    payload = {'newsletter':newsletter, 'emails':emails}
    return render(request, 'newsletter_preview.html', payload)



@permission_required('sito.add_newsletter')
def newsletter_copy(request, id):
    newsletter = Newsletter.objects.get(pk=id)
    
    destinatari = newsletter.destinatari.all()
    allegati = newsletter.allegati.all()

# Duplico la newsletter, cambiando data    
    new_newsletter = newsletter
    new_newsletter.pk = None
    new_newsletter.data_aggiornamento = datetime.now()
    new_newsletter.data_spedizione = None
    new_newsletter.save()

# Duplico tutti i destinatari e li associo alla NUOVA newsletter   
    for destinatario in destinatari:
        destinatario.pk = None
        destinatario.newsletter = new_newsletter
        destinatario.save()

# Duplico tutti i file e li associo alla NUOVA newsletter   
    for allegato in allegati:
        allegato.pk = None
        allegato.newsletter = new_newsletter
        allegato.save()
    
    return redirect(new_newsletter)




@permission_required('sito.change_newsletter')
def newsletter_send(request, id):
    BATCH_SIZE = 30
    
    newsletter = Newsletter.objects.get(pk=id)
    
    destinatari = DestinatarioNewsletter.objects.filter(newsletter=newsletter)
    emails = []
    for d in destinatari:
        email = None
        if d.email:
            email = d.email
        elif d.cliente and d.cliente.email:
            email = '%s <%s>' % (d.cliente.ragsoc, d.cliente.email)
        elif d.persona and d.persona.email:
            email = '%s <%s>' % (d.persona.nome, d.persona.email)
        if email:
            emails.append(email)

    msg = None
    if request.method == 'POST':
        from django.core.mail.message import EmailMessage
        from django.template.defaultfilters import filesizeformat
        import os

        mittente_full = '%s <%s>' % (newsletter.mittente_nome, newsletter.mittente_email)
        msg = EmailMessage(subject=newsletter.oggetto, body=newsletter.testo, to=[mittente_full], from_email=mittente_full, bcc=emails)
        msg.content_subtype = "html"

# Salvo subito i dati della mail, poi il testo viene modificato aggiungendo il link agli allegati
        newsletter.data_spedizione = datetime.now()
        newsletter.save()

# File aggiunti come allegati, inclusi nella mail
        if not newsletter.link_allegati:
            for all in newsletter.allegati.all():
                full_filename = os.path.join(settings.MEDIA_ROOT, all.file_obj.path)
                msg.attach_file(full_filename)
# File aggiunti come link (rimangono sul server) 
        else:
            newsletter.add_linked_files(request)
            msg.body = newsletter.testo
            
# Tutto in Calibri, a Giovanni piace così
        msg.body = '<div style="font-family: Calibri, sans-serif">' + msg.body + '</div>'
        
# Aggiungo la firma, se c'è
        if newsletter.firma:
            msg.body += newsletter.firma.testo        
        
        localize_html_email_images(msg)
        
# Spedisco a blocchi        
        blocks = [emails[i:i+BATCH_SIZE] for i in range(0, len(emails), BATCH_SIZE)]
        for block in blocks:
            msg.bcc = block
            msg.send()
            
    messages.success(request, 'Mail inviata a %d destinatari' % len(emails))

    payload = {'newsletter':newsletter, 'emails':emails, 'msg':msg}
    return render(request, 'newsletter_send.html', payload)




@permission_required('sito.change_newsletter')
def newsletter_testsend(request, id):
    newsletter = Newsletter.objects.get(pk=id)
    
    email = request.POST.get('email')
    # TODO controllare che sia una mail valida
    msg = None
    if request.method == 'POST' and email:
        from django.core.mail.message import EmailMessage
        from django.template.defaultfilters import filesizeformat
        import os

        mittente_full = '%s <%s>' % (newsletter.mittente_nome, newsletter.mittente_email)
        msg = EmailMessage(subject=newsletter.oggetto, body=newsletter.testo, to=[mittente_full], from_email=mittente_full, bcc=[email])
        msg.content_subtype = "html"

# File aggiunti come allegati, inclusi nella mail
        if not newsletter.link_allegati:
            for all in newsletter.allegati.all():
                full_filename = os.path.join(settings.MEDIA_ROOT, all.file_obj.path)
                msg.attach_file(full_filename)
# File aggiunti come link (rimangono sul server) 
        else:
            newsletter.add_linked_files(request)
            msg.body = newsletter.testo
            
# Tutto in Calibri, a Giovanni piace così
        msg.body = '<div style="font-family: Calibri, sans-serif">' + msg.body + '</div>'

# Aggiungo la firma, se c'è
        if newsletter.firma:
            msg.body += newsletter.firma.testo
            
        
        localize_html_email_images(msg)
        
        msg.send()
    messages.success(request, 'Mail di test inviata a %s' % email)

    payload = {'newsletter':newsletter}
    return render(request, 'newsletter_send.html', payload)



#
# START immagini inline nella mail
# http://djangosnippets.org/snippets/2661/
#

import string
import random

def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))
    

def localize_html_email_images(message):
    """Replace linked images served locally with attached images"""

    import re, os.path
    from email.MIMEImage import MIMEImage

    image_pattern = """<img\s*.*src=['"](?P<img_src>%s[^'"]*)['"].*\/>""" % settings.MEDIA_URL
    image_matches = re.findall(image_pattern, message.body)

    added_images = {}

    for image_match in image_matches:
        if image_match not in added_images:
            img_content_cid = id_generator()
            on_disk_path = os.path.join(settings.MEDIA_ROOT, image_match.replace(settings.MEDIA_URL, ''))
            img_data = open(on_disk_path, 'rb').read()
            img = MIMEImage(img_data)
            img.add_header('Content-ID', '<%s>' % img_content_cid)
            img.add_header('Content-Disposition', 'inline')
            message.attach(img)

            added_images[image_match] = img_content_cid

    def repl(matchobj):
        x = matchobj.group('img_src')
        y = 'cid:%s' % str(added_images[matchobj.group('img_src')])
        return matchobj.group(0).replace(matchobj.group('img_src'), 'cid:%s' % added_images[matchobj.group('img_src')])

    if added_images:
        message.body = re.sub(image_pattern, repl, message.body)


#
# END immagini inline nella mail
#

def getInfoUtente(azienda):
    info_utente = {}
    records = InformazioneUtente.objects.filter(azienda = azienda)

    for r in records:
        if r.tipo == 'C':
            value = r.valore_char
        if r.tipo == 'T':
            value = r.valore_text
        if r.tipo == 'I':
            value = r.valore_image
        if r.tipo == 'B':
            value = r.valore_boolean
        info_utente[r.codice] = value
        
    return info_utente


@permission_required('sito.change_informazioneutente')
def info_utente_listing(request):
    azienda = request.user.azienda_set.first()
    info_utente = InformazioneUtente.objects.filter(azienda = azienda)

    payload = {'info_utente':info_utente, 'azienda':azienda}
    return render(request, 'info_utente.html', payload)


@permission_required('sito.change_informazioneutente')
def info_utente_edit(request, id=None):
    cancel_link = reverse('info_utente')
    info_utente = InformazioneUtente()
    if id:
        info_utente = InformazioneUtente.objects.get(pk=id)
        
    form = InformazioneUtenteForm(instance=info_utente)
    if request.method == 'POST':
        form = InformazioneUtenteForm(request.POST, request.FILES, instance=info_utente)
        if form.is_valid():
            info_utente = form.save()
            return redirect(reverse('info_utente'))
    payload = {'form':form, 'cancel_link': cancel_link}
    return render(request, 'edit.html', payload)




#
# START gestione offerte
#
@permission_required('sito.change_offerta')
def offerte_listing(request):
    from dateutil.parser import parse as parse_date

    azienda = request.user.azienda_set.first()
    
    if request.user.has_perm('sito.view_all_groups'):
        gruppi = Gruppo.objects.filter(azienda = azienda).order_by('nome')
        offerte = Offerta.objects.filter(cliente__gruppo__azienda=azienda)
    else:
        gruppi = Gruppo.objects.filter(users = request.user).order_by('nome')
        offerte = Offerta.objects.filter(cliente__gruppo__users = request.user)

    nome = request.GET.get('nome')
    if nome:
        offerte = offerte.filter(cliente__ragsoc__icontains = nome)

    if request.GET.has_key('confermata'):
        offerte = offerte.filter(confermata = True)
        
    gruppo_id = request.GET.get('gruppo')
    if gruppo_id and gruppo_id.isdigit():
        offerte = offerte.filter(cliente__gruppo__id = gruppo_id)

    date_range = request.GET.get('date')
    if date_range:
        tokens = date_range.split('-')
        if len(tokens) == 2:
            start_date_str, end_date_str = tokens
            start_date = parse_date(start_date_str, dayfirst=True)
            end_date = parse_date(end_date_str, dayfirst=True)
            offerte = offerte.filter(data__gte = start_date, data__lte = end_date)
        
        
    payload = {'offerte':offerte, 'gruppi':gruppi}
    return render(request, 'offerte.html', payload)



@permission_required('sito.change_offerta')
def rigoofferta_delete(request, offerta_id, rigo_id):
    offerta = Offerta.objects.get(pk=offerta_id)
    rigo = RigoOfferta.objects.get(pk=rigo_id)
    if rigo.offerta == offerta:
        rigo.delete()
    return redirect(offerta)


@permission_required('sito.add_offerta')
def offerta_copy(request, cliente_id, offerta_id):
    offerta = Offerta.objects.get(pk=offerta_id)
    righi = offerta.rigoofferta_set.all()

# Duplico l'offerta, cambiando titolo e data
    new_offerta = offerta
    new_offerta.pk = None
    new_offerta.numero_documento = "Copia di " + offerta.numero_documento
    new_offerta.data = datetime.now()
    new_offerta.save()
    
# Duplico tutti i righi e li associo alla NUOVA offerta   
    for rigo in righi:
        rigo.pk = None
        rigo.offerta = new_offerta
        rigo.save()
    
    return redirect(new_offerta)




@permission_required('sito.add_offerta')
def offerta_copy_other(request, cliente_id, offerta_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    request.session['offerta_id_copied'] = offerta_id
  
    return redirect(cliente)


@permission_required('sito.add_offerta')
def offerta_paste(request, cliente_id):

    cliente = Cliente.objects.get(pk=cliente_id)
    offerta_id = request.session.get('offerta_id_copied')
    
    
    print "Non va"
    if offerta_id:
        print "Vai con l'foferta"
        offerta = Offerta.objects.get(pk=offerta_id) 
        righi = offerta.rigoofferta_set.all()
    
    # Duplico l'offerta, cambiando titolo e data
        new_offerta = offerta
        new_offerta.pk = None
        new_offerta.cliente = cliente
        new_offerta.numero_documento = "Copia di " + offerta.numero_documento
        new_offerta.data = datetime.now()
        new_offerta.save()
        
    # Duplico tutti i righi e li associo alla NUOVA offerta   
        for rigo in righi:
            rigo.pk = None
            rigo.offerta = new_offerta
            rigo.save()
    # Elimino l'id dalla sessione
        del request.session['offerta_id_copied']

    return redirect(cliente)



@permission_required('sito.add_offerta')
def offerta_cancel_copy(request, cliente_id):
    del request.session['offerta_id_copied']
    cliente = Cliente.objects.get(pk=cliente_id)
    messages.success(request, "Copia annullata.")
    return redirect(cliente)


@login_required
@permission_required('sito.change_offerta')
@csrf_exempt
def offerta_sort_righi(request):
    id_righi = request.POST.getlist('id')
    for i, id_rigo in enumerate(id_righi):
        try:
            rigo = RigoOfferta.objects.get(pk=id_rigo)
            rigo.ordine = i
            rigo.save()
        except ObjectDoesNotExist:
            pass
    if request.is_ajax():
        return HttpResponse('OK')


@permission_required('sito.delete_offerta')
def offerta_delete(request, cliente_id, offerta_id):
    cliente = Cliente.objects.get(pk=cliente_id)
    offerta = Offerta.objects.get(pk=offerta_id)
    if request.method == 'POST':
        offerta.delete()
        messages.success(request, "Offerta eliminata.")
        return redirect(cliente)
        
        
def offerta_view(request, cliente_id, offerta_id=None, rigo_id=None, format=None):

    if not request.user.is_authenticated() and format != 'pdf':
        return HttpResponseForbidden("Non puoi visualizzare questa pagina.")

    cliente = Cliente.objects.get(pk=cliente_id)
    if offerta_id:
        offerta = Offerta.objects.get(pk=offerta_id)
    else:
        timestamp = datetime.now().strftime('%H%M%d%m%Y')
        offerta = Offerta(cliente=cliente, numero_documento=timestamp)

    totale_imponibile = totale_iva = totale_offerta = max_sconti = 0


    offerta_form = OffertaForm(instance=offerta, user=request.user)
    if request.method == 'POST':
        offerta_form = OffertaForm(request.POST, instance=offerta, user=request.user)
        if offerta_form.is_valid():
            offerta_form.save()
            messages.success(request, "Offerta modificata.")
        else:
            messages.error(request, "Ci sono errori nel modulo, controlla i campi indicati.")
            

    
    info_utente = getInfoUtente(offerta.cliente.gruppo.azienda)

#
# Nuova gestione righi
#
# Tre righi extra se nuova offerta, altrimenti nessuno

    extra = format != 'pdf' and 3 or 0
    print "NE aggiungo %d" % extra

#    RigoOffertaFormSet = inlineformset_factory(Offerta, RigoOfferta, form=RigoOffertaInlineForm, extra=not offerta.pk and 3 or 0, exclude=('offerta',))
    RigoOffertaFormSet = inlineformset_factory(Offerta, RigoOfferta, form=RigoOffertaInlineForm, extra=extra, exclude=('offerta',))

    formset = RigoOffertaFormSet(instance=offerta)

    if request.method == 'POST':
        formset = RigoOffertaFormSet(request.POST, instance=offerta)
#        for form in formset:
#            form.empty_permitted = False
        if formset.is_valid():
            formset.save()
            return redirect(offerta)
        else:
            messages.error(request, "Ci sono errori nel modulo, controlla i campi indicati.")
            print formset.errors

# 24.7.2016 - Non voglio vedere form vuoti dopo il salvataggio
#        return redirect(offerta)
#            formset = RigoOffertaFormSet(instance=offerta)

            
    info_utente = getInfoUtente(offerta.cliente.gruppo.azienda)

# Calcolo riepilogo IVA
    riepilogo_iva_dict = {}
    riepilogo_iva = []

    for form in formset:
        rigo = form.instance
        prezzo_netto = rigo.prezzo
        if rigo.sconto1:
            max_sconti = max(max_sconti, 1)
            prezzo_netto = prezzo_netto * (100 - rigo.sconto1) / 100
        if rigo.sconto2:
            max_sconti = max(max_sconti, 2)
            prezzo_netto = prezzo_netto * (100 - rigo.sconto2) / 100
        if rigo.sconto3:
            max_sconti = max(max_sconti, 3)
            prezzo_netto = prezzo_netto * (100 - rigo.sconto3) / 100
        if rigo.sconto4:
            max_sconti = max(max_sconti, 4)
            prezzo_netto = prezzo_netto * (100 - rigo.sconto4) / 100
        rigo.prezzo_netto = prezzo_netto
        rigo.prezzo_totale = prezzo_netto * rigo.quantita
        
        aliquota = rigo.aliquota_iva
        if aliquota in riepilogo_iva_dict:
            riepilogo_iva_dict[aliquota] += rigo.prezzo_totale
        else:
            riepilogo_iva_dict[aliquota] = rigo.prezzo_totale


    aliquote = riepilogo_iva_dict.keys()
    aliquote.sort(lambda x,y:cmp(x.isdigit() and int(x) or 0, y.isdigit() and int(y) or 0))
    aliquote.reverse()

    totali = {}
    for aliquota in aliquote:
        try:
            aliquota_int = int(aliquota)
        except:
            aliquota_int = 0
        rigo_iva = {'aliquota':aliquota, 'imponibile':riepilogo_iva_dict[aliquota], 'iva':riepilogo_iva_dict[aliquota] * aliquota_int / 100}
        riepilogo_iva.append(rigo_iva)
        totale_imponibile += rigo_iva['imponibile']
        totale_iva += rigo_iva['iva']        

    # Calcolo IVA mista
    riepilogo_iva_mista_dict = {'ALT': 0, 'MBS':0, 'SIG':0}
    riepilogo_iva_tot = {'ALT': 0, 'MBS':0, 'SIG':0}
    has_iva_mista = False

    for form in formset:
        rigo = form.instance

        if rigo.aliquota_iva in ('ALT', 'MAB'):
            riepilogo_iva_tot['ALT'] += rigo.prezzo_totale
        elif rigo.aliquota_iva == 'MBS':
            riepilogo_iva_tot['MBS'] += rigo.prezzo_totale
        elif rigo.aliquota_iva == 'SIG':
            riepilogo_iva_tot['SIG'] += rigo.prezzo_totale
            has_iva_mista = True


    riepilogo_iva_mista_dict['ALT'] = riepilogo_iva_tot['ALT']
    riepilogo_iva_mista_dict['MBS'] = min(riepilogo_iva_tot['MBS'] * 2, totale_imponibile - riepilogo_iva_tot['ALT'])
    riepilogo_iva_mista_dict['SIG'] = riepilogo_iva_tot['SIG'] + riepilogo_iva_tot['MBS'] - riepilogo_iva_mista_dict['MBS']

 #   print 'riepilogo_iva_mista_dict', riepilogo_iva_mista_dict
 #   print 'riepilogo_iva_tot', riepilogo_iva_tot

    if has_iva_mista:
        riepilogo_iva = [
            {'imponibile': riepilogo_iva_mista_dict['SIG'], 'aliquota': 22, 'iva': riepilogo_iva_mista_dict['SIG'] * 22 / 100},
            {'imponibile': riepilogo_iva_mista_dict['MBS'], 'aliquota': 10, 'iva': riepilogo_iva_mista_dict['MBS'] * 10 / 100},            
            {'imponibile': riepilogo_iva_mista_dict['ALT'], 'aliquota': 10, 'iva': riepilogo_iva_mista_dict['ALT'] * 10 / 100},            
            ]
        totale_iva = sum([r['iva'] for r in riepilogo_iva])

    totale_offerta = float(totale_imponibile + totale_iva)


    payload = {'offerta': offerta, 'cliente':cliente, 'riepilogo_iva':riepilogo_iva, 'totale_imponibile':totale_imponibile, 'totale_iva':totale_iva, 'totale_offerta':totale_offerta, 'info_utente':info_utente, 'info_utente':info_utente,
    'offerta_form':offerta_form, 'max_sconti':max_sconti, 'formset':formset, 'has_iva_mista':has_iva_mista}
    
        
    if format == 'pdf':
        return payload
    else:
        return render(request, 'offerta.html', payload)




# Vista alternativa usando tabelle, per poi esportare in pdf
def offerta_pdf_layout(request, cliente_id, offerta_id):
    payload = {}
# La mostro solo se sono autenticato oppure viene chiamata dallo stesso server (per generare il pdf)
#    if request.user.is_authenticated() or request.META['REMOTE_ADDR'] == '204.11.56.48':
#        payload = offerta_view(request, cliente_id, offerta_id, format='pdf')

    payload = offerta_view(request, cliente_id, offerta_id, format='pdf')
    return render(request, 'offertapdf.html', payload)




@login_required
def offerta_pdf(request, cliente_id, offerta_id):
    from subprocess import Popen, PIPE, STDOUT    
    import os
    
    cliente = Cliente.objects.get(pk=cliente_id)
    offerta = Offerta.objects.get(pk=offerta_id)
    
    url = 'http://sunlife.infofactory.it/cliente/%s/offerte/%s/pdf_layout' % (cliente_id, offerta_id)
    
    url = reverse('offerta_pdf_layout', kwargs={'cliente_id':cliente_id, 'offerta_id':offerta_id})  
    url = 'http://%s%s' % (request.get_host(), url)
    
    
    print url
    
#    filename = '/tmp/offerta-%s.pdf' % offerta_id
    filename = '/home/nello/sunlife/tmp/offerta-%s.pdf' % offerta_id
    
    print "Filename: %s" % filename
    
    
#    cmd = '/home/nello/wkhtmltopdf.sh %s %s' % (url, filename)

    cmd = '/home/nello/wkhtmltox/bin/wkhtmltopdf %s %s' % (url, filename)


    print "CMD: %s" % cmd
    
    
    p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
    debug = p.stdout.read()    
    pdf_file = open(filename)
    pdf_content = pdf_file.read()
    pdf_file.close()
    os.remove(filename)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=offerta-%s-%s.pdf' % (offerta.data.strftime('%d-%m-%Y'), slugify(cliente.ragsoc))
    return response


#
# END gestione offerte
#



#
# Gestione listini e prodotti
#
def listini_listing(request):
    listini = Listino.objects.all()
    payload = {'listini': listini}
    return render(request, 'listini.html', payload)


def prodotti_listing(request, id=None):

    listino = None
    query = request.GET.get('query')
    if query:
        prodotti = Prodotto.objects.filter(Q(descrizione__icontains = query) | Q(codice__icontains = query))    
    else:
        prodotti = Prodotto.objects.all()
    if id:
        prodotti = prodotti.filter(listino__id = id)
        listino = Listino.objects.get(pk=id)

# Ricerca con autocomplete
    term = request.GET.get('term')
    if term:
        field = request.GET.get('field')
        if field == 'descrizione':
            prodotti = Prodotto.objects.filter(descrizione__icontains = term, attivo=True)
        else:
            prodotti = Prodotto.objects.filter(codice__icontains = term, attivo=True)
        
        prodotti_json = []
        for prodotto in prodotti:
            if field == 'descrizione':
                value = prodotto.descrizione
            else:
                value = prodotto.codice
            
            prodotto_json = {'value':value, 'label':'%s - %s' % (prodotto.descrizione, prodotto.listino.marchio),
                'codice':prodotto.codice, 'descrizione':prodotto.descrizione, 'prezzo':float(prodotto.prezzo), 'marchio':prodotto.listino.marchio}
            prodotti_json.append(prodotto_json)

        return send_json_response(prodotti_json)

    payload = {'prodotti': prodotti, 'listino':listino}
    return render(request, 'prodotti.html', payload)



def listino_add(request):
 
    form = ListinoForm()
    listino = None
    
    payload = {'errors':{}, 'form':form}
    if request.method == 'POST':
        form = ListinoForm(request.POST, request.FILES)
        payload['form'] = form
        
        if form.is_valid():
            listino = form.save()
            return redirect('listino_columns', id=listino.pk)    

    return render(request, 'prodotti_upload.html', payload)    


def listino_edit(request, id):
    listino = Listino.objects.get(pk=id)    
    form = ListinoForm(instance=listino)
    cancel_link = reverse('listini_listing')
    
    payload = {'form':form, 'cancel_link':cancel_link}
    if request.method == 'POST':
        if request.POST.get('action') == 'delete':
            listino.delete()
            messages.success(request, "Listino eliminato.")
            return redirect('listini_listing')
        
        form = ListinoForm(request.POST, request.FILES, instance=listino)
        payload['form'] = form
        
        if form.is_valid():
            listino = form.save()
            # Aggiorna lo stato di tutti i prodotti del listino
            listino.prodotto_set.all().update(attivo=listino.attivo)
                
            messages.success(request, "Listino modificato.")
            return redirect('listini_listing')    

    return render(request, 'edit.html', payload)





def listino_columns(request, id):
    """Permette di selezionare le colonne da importare"""
    import xlrd

    listino = Listino.objects.get(pk=id)

# Salvo l'Excel in un file temporaneo
    excel_file = listino.file
    tmp_filename = '/tmp/%s-listino.xls' % (request.user.username)
    with open(tmp_filename, 'wb+') as destination:
        for chunk in excel_file.chunks():
            destination.write(chunk)

# Apro l'Excel e leggo le prime 20 righe
    wb = xlrd.open_workbook(tmp_filename)
    sh = wb.sheet_by_index(0)
    table_data = []
    for rownum in range(1, sh.nrows):
        fields = sh.row_values(rownum)
        table_data.append(fields)

    table_data = table_data[:20]
    payload = {'table_data': table_data, 'listino': listino}
    return render(request, 'listino_columns.html', payload)    


def listino_import(request, id):
    """Importa i prodotti (previa verifica) caricati tramite file Excel"""
    import xlrd
    from types import FloatType, IntType, StringType, UnicodeType

    listino = Listino.objects.get(pk=id)

    prodotti = []
    confirm = False
    existing = 0

    if request.method == 'POST':
    
        if request.POST.has_key('confirm'):
            confirm = True
            listino.attivo = True
            listino.save()
        
# Controllo se tutte e tre le colonne sono state selezionate
        cols = [k for k in request.POST.keys() if k.startswith('col-')]
        
        codice_index, descrizione_index, prezzo_index = -1, -1, -1
        for k, v in request.POST.iteritems():
            if k.startswith('col-'):
                index = int(k.split('-')[-1])
                if v == 'codice':
                    codice_index = index
                if v == 'descrizione':
                    descrizione_index = index
                if v == 'prezzo':
                    prezzo_index = index
        
        
        if codice_index == -1 or descrizione_index == -1 or prezzo_index == -1:
            payload = {'errors': 'Devi selezionare tutte e tre le colonne (Codice, Descrizione e Prezzo). Ricarica il file.'}
            return render(request, 'prodotti_upload.html', payload)    
        else:
            
        # Salvo l'Excel in un file temporaneo
            excel_file = listino.file
            tmp_filename = '/tmp/%s-listino.xls' % (request.user.username)
            with open(tmp_filename, 'wb+') as destination:
                for chunk in excel_file.chunks():
                    destination.write(chunk)
                    
            wb = xlrd.open_workbook(tmp_filename)
            sh = wb.sheet_by_index(0)
            
            for rownum in range(sh.nrows):
                fields = sh.row_values(rownum)

                codice = fields[codice_index]
                descrizione = fields[descrizione_index]
                prezzo = fields[prezzo_index]
                
                if type(codice) in (StringType, UnicodeType):
                    codice = codice.strip()
                if type(descrizione) in (StringType, UnicodeType):
                    descrizione = descrizione.strip()
                if type(prezzo) in (StringType, UnicodeType):
                    prezzo = prezzo.strip()

                # Nel listino Chaffoteaux il codice è un intero, ma viene letto come decimale, aggiungendo un ".0"
                try:
                    codice = str(int(codice))
                except:
                    pass
                    
# Evita il tutto maiuscole se ci sono più di 4 parole (perché descrizioni brevi sono sigle dei modelli)
                if len(descrizione.split()) > 4 and descrizione == descrizione.upper():
                    descrizione = descrizione.capitalize()
                
#                print "Codice: %s, Descrizione: %s, Prezzo: %s" % (codice, descrizione, prezzo)
                
                if codice and descrizione: # 19.7.2016 - Vanno bene anche prezzi a zero
                    prodotto = Prodotto(listino=listino, codice=codice, descrizione=descrizione, prezzo=prezzo)
# Prezzo potrebbe essere non valido come numero (es. righe di intestazione)
                    if type(prezzo) in (FloatType, IntType):
                        prodotti.append(prodotto)
                        
                        if confirm:
                            prodotto.save()

    payload = {'listino':listino, 'prodotti': prodotti, 'existing': existing, 'confirm':confirm, 'col_fields':{}}
    
    col_fields = [k for k in request.POST.keys() if k.startswith('col-')]
    for col_field in col_fields:
        payload['col_fields'][col_field] = request.POST.get(col_field)

    return render(request, 'prodotti_verify.html', payload)    



#
# START Estensione maggio 2018 - Attività clienti
#

@permission_required('sito.change_attivita')
def attivita_edit(request, cliente_id, attivita_id=None):

    cliente = Cliente.objects.get(pk=cliente_id)
    attivita = None
    if attivita_id:
        attivita = Attivita.objects.get(pk=attivita_id)

    payload = {'cliente': cliente}

    return render(request, 'cliente.html', payload)










#
# END Estensione maggio 2018 - Attività clienti
#
    
def import_aziende(request):
    import xlrd
    IMPORT_FOLDER = "/home/nello/lazzari"
    filename = 'fvg.xls'
    file_path = os.path.join(IMPORT_FOLDER, filename)
    debug = []

    try:
        wb = xlrd.open_workbook(file_path)
    except IOError:
        debug.append("File %s non trovato" % file_path)
        wb = None

    if wb:

        sh = wb.sheet_by_index(0)

        for rownum in range(1, sh.nrows):
            fields = sh.row_values(rownum)
            ragsoc, indirizzo, cap, citta, provincia, telefono, email = fields      

# Aggiustamenti
            ragsoc = ragsoc.replace('S.R.L.', 'srl').replace('S.A.S.', 'sas').replace('S.N.C.', 'snc')
            indirizzo = indirizzo.title()
            try:
                cap = str(int(cap))
            except:
                pass

# Solo il primo numero di telefono (sono separati da virgola)
            telefono = telefono.replace('-', ',')
            telefono = telefono.split(',')[0].strip()
            
            if len(telefono) > 20:
                telefono = telefono[:20]
        
            data = [ragsoc, indirizzo, cap, citta, provincia, telefono, email]
            debug.append(data)
            
            
            gruppo = Gruppo.objects.get(pk=20) # Nuovi installatori termoidraulici
            cliente = Cliente(ragsoc=ragsoc, indirizzo=indirizzo, cap=cap, citta=citta, provincia=provincia, telefono=telefono, email=email, gruppo=gruppo)
            cliente.save()

    payload = {'debug':debug}
    
    return render(request, 'index.html', payload)


#
#
#
#
#from sito.views import import_listino
#file_path = '/home/nello/sunlife/listini/listino-mescoli.xls'
#import_listino(file_path)


def import_listino(file_path):
    import xlrd

    marchio = None
    wb = None
    try:
        wb = xlrd.open_workbook(file_path)
    except IOError:
        print "File %s non trovato" % file_path

    if wb:

        sh = wb.sheet_by_index(0)

        if 'mescoli' in file_path:
            marchio = Marchio.objects.get(nome='Mescoli')       
        if 'idealclima' in file_path:
            marchio = Marchio.objects.get(nome='IdealClima')

        if 'chaffoteaux' in file_path:
            marchio = Marchio.objects.get(nome='Chaffoteaux')

        if marchio:
            for rownum in range(1, sh.nrows):
                fields = sh.row_values(rownum)
                if marchio.nome == 'Mescoli':
                    if len(fields) == 3 and type(fields[2]) == type(1.5):
                        codice, descrizione, prezzo = fields
                        prodotto = Prodotto(codice=codice, descrizione=descrizione, prezzo=prezzo, marchio=marchio)
                        prodotto.save()

                if marchio.nome == 'IdealClima':
                    if len(fields) == 8 and type(fields[6]) == type(1.5):
                        codice, dummy, descrizione, dummy, dummy, dummy, prezzo, dummy = fields
                        prodotto = Prodotto(codice=codice, descrizione=descrizione, prezzo=prezzo, marchio=marchio)
                        prodotto.save()    

# Ha 5 fogli, prendo per ora solo il primo
                if marchio.nome == 'Chaffoteaux':
                    if len(fields) >= 3 and type(fields[2]) == type(1.5):
                        codice, descrizione, prezzo = fields[:3]
                        # Il codice è un intero, ma viene letto come decimale, aggiungendo un ".0"
                        try:
                            codice = str(int(codice))
                        except:
                            pass
                        prodotto = Prodotto(codice=codice, descrizione=descrizione, prezzo=prezzo, marchio=marchio)
                        prodotto.save()  
 
 
 
        print "Fatto"
        
        
        
        
#
# Funzioni per le chiamate JSON
#
def send_json_response(data):    
    import json
    json_data = json.dumps(data)
    response = HttpResponse(json_data, content_type='application/json')
    return response
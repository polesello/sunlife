from django.shortcuts import render, redirect
from django.urls import reverse
from django.db.models import Q, Count
from django.core.paginator import Paginator

from gestione.forms import ClienteSearchForm

from home.models import Cliente, Offerta, ALIQUOTE_IVA
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages
from django.utils import timezone

def index(request):
    return redirect(reverse('gestione:clienti'))

def clienti(request):
    clienti = Cliente.objects.all().select_related('gruppo').annotate(num_persone=Count('persone', distinct=True),num_offerte=Count('offerte', distinct=True)).order_by('-updated', 'ragsoc')
    form = ClienteSearchForm(request.GET or None)

    if form.is_valid():
        query = form.cleaned_data.get('query')
        gruppo = form.cleaned_data.get('gruppo')
        intervento = form.cleaned_data.get('intervento')
        segnalazione = form.cleaned_data.get('segnalazione')
        prodotto = form.cleaned_data.get('prodotto')

        if query:
            words = query.split()
            for word in words:
                clienti = clienti.filter(Q(ragsoc__icontains=word) | Q(citta__icontains=word) | Q(telefono__icontains=word) | Q(email__icontains=word) | Q(piva__icontains=word) | Q(cf__icontains=word) | Q(persone__nome__icontains=word))

        if gruppo:
            clienti = clienti.filter(gruppo=gruppo)

        if intervento:
            clienti = clienti.filter(richieste=intervento)

        if segnalazione:
            clienti = clienti.filter(segnalazione=segnalazione)

        if prodotto:
            words = prodotto.split()
            for word in words:
                clienti = clienti.filter(offerte__righe__descrizione__icontains=word)
 
    # Redirect alla scheda cliente se c'è un solo risultato
    if clienti.count() == 1:
        return redirect(reverse('gestione:cliente_view', args=[clienti.first().id]))


    page = request.GET.get('page', 1)
    paginator = Paginator(clienti, 50)
    clienti = paginator.get_page(page)
    page_range = paginator.get_elided_page_range(number=page)


    context = {
        'clienti': clienti,
        'form': form,
        'page_range': page_range
    }

    return render(request, 'gestione/clienti.html', context)

def cliente_view(request, id):
    import json
    from home.models import TipoAttivita, Agente, Segnalazione

    cliente = Cliente.objects.get(pk=id)

    # Eventuale offerta da copiare da un altro cliente, messa negli appunti
    offerta_id_copied = request.session.get('offerta_id_copied')
    offerta_copied = None
    if offerta_id_copied:
        # 1.2.2021 - Nel caso l'avesse già cancellata
        try:
            offerta_copied = Offerta.objects.get(pk=offerta_id_copied)
        except:
            pass

    context = {
        'offerta_copied': offerta_copied,
        'cliente': cliente,
        'cliente_json': json.loads(cliente.to_json()),
        'liste_json': {
            'tipi_attivita': {int(t.id):t.nome for t in TipoAttivita.objects.all()},
            'agenti': {int(a.id):a.nome for a in Agente.objects.filter(attivo=True)},
            'segnalazioni': {int(s.id):s.nome for s in Segnalazione.objects.all()},
        }
    }
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(context['cliente_json'])
    return render(request, 'gestione/cliente_view.html', context)

@csrf_exempt
def cliente_edit(request, id):
    if request.method == 'POST':
        if 'file' in request.FILES:
            from home.models import DocumentoCliente
            documento = DocumentoCliente.objects.create(cliente_id=id, file=request.FILES['file'], nome=request.FILES['file'].name)
            print(documento)
            return JsonResponse({'id': documento.id, 'file': documento.file.name, 'nome': documento.nome})
        
        cliente = Cliente.from_json(request.body)
        cliente.save(update_fields=['persone', 'attivita', 'indirizzi', 'documenti', 'ragsoc', 'indirizzo', 'citta', 'cap', 'provincia', 'telefono', 'email', 'piva', 'cf', 'note', 'note_private', 'gruppo', 'updated', 'banca', 'iban', 'pec', 'sdi', 'segnalazione'])
        return JsonResponse({'success': True, 'cliente': id})
    return HttpResponse(status=405)


def cliente_delete(request, id):
    cliente = Cliente.objects.get(pk=id)
    ragsoc = request.POST.get('ragsoc', '')
    if ragsoc.lower() != cliente.ragsoc.lower():
        messages.error(request, 'Il nome cliente non corrisponde')
        return redirect(reverse('gestione:cliente_view', args=[id]))
    
    cliente.delete()
    messages.success(request, 'Cliente eliminato')
    return redirect(reverse('gestione:clienti'))


def offerta_edit(request, id, offerta_id=None):
    cliente = Cliente.objects.get(pk=id)

    if offerta_id:
        offerta = cliente.offerte.get(pk=offerta_id)
    else:
        offerta = Offerta.objects.create(cliente=cliente, titolo='Nuova offerta')
        return redirect(reverse('gestione:offerta_edit', args=[id, offerta.id]))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(json.loads(offerta.to_json()), safe=False)
    
    if request.method == 'POST':
        offerta = Offerta.from_json(request.body)
        print('caricato')
        print(offerta)
        offerta.pk = offerta_id
        offerta.save()
        return JsonResponse({'success': True, 'offerta': offerta.id})


    context = {
        'cliente': cliente,
        'offerta': offerta,
        'offerta_json': json.loads(offerta.to_json()),
        'cliente_json': json.loads(offerta.cliente.to_json()),
        'aliquote_iva': ALIQUOTE_IVA
    }
    return render(request, 'gestione/offerta_edit.html', context)


def offerta_delete(request, id, offerta_id):
    cliente = Cliente.objects.get(pk=id)
    offerta = cliente.offerte.get(pk=offerta_id)
    offerta.delete()
    messages.success(request, 'Offerta eliminata')
    return redirect(reverse('gestione:cliente_view', args=[id]))


def offerta_copy(request, id, offerta_id):
    cliente = Cliente.objects.get(pk=id)
    offerta = cliente.offerte.get(pk=offerta_id)
    offerta.pk = None
    offerta.titolo = f'{offerta.titolo} - Copia'
    offerta.data = timezone.now()
    offerta.confermata = False
    offerta.save()

    # Copia righe
    vecchia_offerta = cliente.offerte.get(pk=offerta_id)
    for riga in vecchia_offerta.righe.all():
        riga.pk = None
        riga.offerta = offerta
        riga.save()
    messages.success(request, 'Offerta copiata')
    return redirect(reverse('gestione:cliente_view', args=[id]))



def offerta_copy_other(request, id, offerta_id):
    request.session['offerta_id_copied'] = offerta_id
    messages.success(request, 'Vai al cliente a cui vuoi copiare l\'offerta')
    return redirect(reverse('gestione:cliente_view', args=[id]))




def offerta_paste(request, id):
    from datetime import datetime

    cliente = Cliente.objects.get(pk=id)
    offerta_id = request.session.get('offerta_id_copied')
    
    
    if offerta_id:
        offerta = Offerta.objects.get(pk=offerta_id) 
        righi = offerta.righe.all()

        print(f"Offerta da copiare: {offerta}")
        print(f"Righe da copiare: {righi}")
    
    # Duplico l'offerta, cambiando titolo e data
        new_offerta = offerta
        new_offerta.pk = None
        new_offerta.cliente = cliente
        new_offerta.numero_documento = "Copia di " + offerta.numero_documento
        new_offerta.data = datetime.now()
        new_offerta.save()
        
    # Duplico tutti i righi e li associo alla NUOVA offerta
    # attenzione che sono dei ParentalKey, quindi non posso fare un save() ma devo fare un update()
        for riga in righi:
            riga.pk = None
            riga.offerta = new_offerta
            print(f"Riga da copiare: {riga}")
            riga.save()

        messages.success(request, "Offerta copiata.")


    # Elimino l'id dalla sessione
        del request.session['offerta_id_copied']

    return redirect(reverse('gestione:cliente_view', args=[id]))



def offerta_cancel_copy(request, id):
    request.session.pop('offerta_id_copied', None)
    messages.success(request, "Copia annullata.")
    return redirect(reverse('gestione:cliente_view', args=[id]))


@csrf_exempt
def doc_edit(request, id, doc_id):
    cliente = Cliente.objects.get(pk=id)
    doc = cliente.documenti.get(pk=doc_id)
    if request.method == 'POST':
        #salva il documentoCliente da json

        data = json.loads(request.body)
        doc.installatore = data.get('installatore')
        doc.privato = data.get('privato')
        doc.nome = data.get('nome')
        doc.save()
        return JsonResponse({'success': True, 'doc': doc_id})
    elif request.method == 'DELETE':
        doc.delete()
        return JsonResponse({'success': True, 'doc': doc_id})
    return JsonResponse({'nome': doc.nome})


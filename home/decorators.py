from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def check_client(view):
    @wraps(view)
    def _wrapped_view(request, *args, **kwargs):
        if kwargs.get('check_session') != False and 'client_id' not in request.session and request.user.is_anonymous:
            messages.error(request, 'Non sei loggato')
            return redirect('/')
        return view(request, *args, **kwargs)
    return _wrapped_view

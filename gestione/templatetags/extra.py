from django.template import Library, Node, Variable
from django.contrib.auth.models import Group
from django.utils import html

register = Library()



# https://djangosnippets.org/snippets/2428/

class AddGetParameter(Node):
    def __init__(self, values):
        self.values = values

    def render(self, context):
        req = Variable('request').resolve(context)
        params = req.GET.copy()
        for key, value in self.values.items():
            params[key] = value.resolve(context)
        return '?%s' % params.urlencode()


@register.tag
def add_get(parser, token):
    pairs = token.split_contents()[1:]
    values = {}
    for pair in pairs:
        s = pair.split('=', 1)
        values[s[0]] = parser.compile_filter(s[1])
    return AddGetParameter(values)


@register.simple_tag(takes_context=True)
def queryfilter(context, field):
    query = context['request'].GET.copy()
    if query.get(field):
        query.pop(field)
    return query.urlencode()


 
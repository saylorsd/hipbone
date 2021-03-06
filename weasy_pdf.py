# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import re, json, tempfile

from .views import AddressForm

from icecream import ic

def generate_pdf(request):
    """Generate a PDF version of a given HTML template."""
    # Collect the information to be included in the template.
    json_parcels = request.POST.get('json_parcels', None)
    parcels = json.loads(json_parcels)
    data = {
        'address_form': AddressForm,
        'search_type': request.POST.get('search_type', None),
        'parcels': parcels,
        'msg': '',
        'output_format': 'pdf'
    }

    # Render the HTML
    html_string = render_to_string('hipbone/pdf_index.html', context = data)
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    stylesheets = ['https://tools.wprdc.org/static/hipbone/css/housing-portal-basic-style.css'] # Hard-code list of CSS stylesheets for now.
    result = html.write_pdf(stylesheets=stylesheets, presentational_hints=True)

    # Create the HTTP response
    response = HttpResponse(content_type='application/pdf;')
    response['Content-Disposition'] = 'inline; filename=housing_information_portal_extract.pdf'
    response['Content-Transfer-Encoding'] = 'binary'

    with tempfile.NamedTemporaryFile(delete=True) as output:
        output.write(result)
        output.flush()
        output = open(output.name, 'rb')
        response.write(output.read())

    return response

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
    parcels = request.POST.get('parcels', None)
    parcels = json.loads(re.sub("'", '"', parcels))
    parcel_id = request.POST.get('parcel_id', None)
    parcel_data = request.POST.get('parcel_data', '{}')
    parcel_data = json.loads(re.sub("'", '"', parcel_data))
    data = {
        'address_form': AddressForm,
        'search_type': request.POST.get('search_type', None),
        'parcel_id': parcel_id,
        'parcel_data': parcel_data,
        'parcels': parcels,
        'msg': ""
    }

    # Render the HTML
    html_string = render_to_string('hipbone/index.html', context = data)
    html = HTML(string=html_string)
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

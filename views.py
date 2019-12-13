from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.views.generic import View
from django.conf import settings

from .forms import LoginForm, AddressForm

import requests, json
from datetime import datetime

from .models import UserLoginActivity
from .tracking_util import save_activity
from .queries import query_db, query_voters, aggregate_voters
from .parameters.local import PRODUCTION

from django.contrib.auth.decorators import login_required

from icecream import ic

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request,
                                username=cd['username'],
                                password=cd['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    save_activity(request)
                    return HttpResponseRedirect('/hipbone')
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid login')
    else:
        form = LoginForm()
    return render(request, 'hipbone/login.html', {'form': form})

def enumerated_row(row, fields):
    return {k: row[field] for k, field in enumerate(fields)}

def convert_to_standard_model(table, fields):
    """To simplify representation of data tables (making the JavaScript
    views simpler), convert the original table, which is in a
    list-of-dicts form, where the key for each field is a name,
    coming from the SQL query, hinting at the meaning of the field,
    to a different list-of-dicts form, where the keys are replaced by
    integers (0 through n-1, where n is the number of fields).

    This ensures that the order of the JavaScript knows what order
    the fields should be in (since Python dicts do not by themselves
    preserve order)."""
    return [enumerated_row(row, fields) for row in table]

def stack(table, name_by_field):
    return [{0 : name, 1 : row[field]} for row in table for field, name in name_by_field.items()]

class IndexView(View):

    def __init__(self):
        self.template_name = 'hipbone/index.html'
        self.msg = ''
        self.form_class = AddressForm
        self.context = { 'parcels': [],
                'msg': self.msg,
                'error_message': '',
                'output_format': 'html'
            }

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('%s?next=%s' % ('/hipbone/login/', request.path))

        form = self.form_class()
        self.context['address_form'] = form
        return render(request, self.template_name, self.context)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('%s?next=%s' % ('/hipbone/login/', request.path))
        form = self.form_class(request.POST)
        error_message = ''
        parcels = []
        if form.is_valid():
            # The form fields passed validation
            search_type = request.POST.get('search_type')
            if search_type == 'address':
                cd = form.cleaned_data
                address = cd['address']
                search_term = address
                url = "https://tools.wprdc.org/geo/geocode?addr={}".format(address)
            else: # Implicitly, search_type == 'parcel'
                cd = form.cleaned_data
                parcel_id = cd['address'] # [ ] Generalize the term 'address' to some include parcel ID
                search_term = parcel_id
                url = "https://tools.wprdc.org/geo/reverse_geocode/?pin={}".format(parcel_id)

            WPRDC_LOOKUP = False
            if not PRODUCTION:
                voters = []
                aggregated_voters = []
                if WPRDC_LOOKUP:
                    response = requests.get(url)
                    if response.status_code != 200:
                        error_message = 'Look-up failed with status code {}.'.format(response.status_code)
                    else:
                        json_response = response.json()
                        if 'data' in json_response: # Parse results of address lookup
                            json_data = json_response['data']
                            if 'parcel_id' in json_data:
                                parcel = {}
                                if 'regions' in json_data and 'us_census_tract' in json_data['regions']:
                                    if 'name' in json_data['regions']['us_census_tract']:
                                        self.parcel_data['Census tract'] = json_data['regions']['us_census_tract']['name']
                                        parcel['parcel_data'] = {'Census tract': json_data['regions']['us_census_tract']['name']}
                                parcels.append(parcel)

                        elif 'results' in json_response: # Parse results of parcel ID lookup
                            json_results = json_response['results']
                            parcel = {}
                            if 'us_census_tract' in json_results:
                                if 'name' in json_results['us_census_tract']:
                                    self.parcel_data['Census tract'] = json_results['us_census_tract']['name']
                                    parcel['parcel_data'] = {'Census tract': json_results['us_census_tract']['name']}
                            parcels.append(parcel)
                else:
                    parcels = []
            else:
                parcels = query_db(search_type, search_term)
                if len(parcels) == 1:
                    d3_id = parcels[0]['d3_id']
                    voters = query_voters(d3_id)
                    aggregated_voters = aggregate_voters(d3_id)
                else:
                    voters = []
                    aggregated_voters = []

        self.context = { 'address_form': form,
                'search_type': search_type,
                'parcels': parcels,
                'json_parcels': json.dumps(parcels), # This is only here to be passed
                # back to weasy_pdf.py, avoiding further queries. If Django templating
                # supporting something like the tojson filter, we could just use that
                # in the template ({{ parcels|tojson|safe }}) instead.
                'voters': voters,
                'aggregated_voters': aggregated_voters,
                'msg': self.msg,
                'error_message': error_message,
                'output_format': 'html'
            }
        post_response = render(request, self.template_name, self.context)
        return post_response

def get_parcels(request):
    """
    Look up the parcel and return its parameters in JSON format for easy asynchronous
    modification of the otherwise unchanged HTML page.
    """
    if not request.user.is_authenticated:
        return {'error_message': "User is not logged in and therefore unable to get this data. Try the /login/ URL."}

    error_message = ''
    search_type = request.GET.get('search_type')
    search_term = request.GET.get('parcel_search_term')
    ic(search_type, search_term)
    #if search_term in [None, '']:
    #    data = {'msg': 'No results.'}
    #    return JsonResponse(data)
    if search_type != 'parcel':
        search_type = 'address'
    ic(search_type)

    if PRODUCTION:
        parcels = query_db(search_type, search_term)
        if len(parcels) > 0:
            d3_id = parcels[0]['d3_id']
            voters = query_voters(d3_id)
            aggregated_voters = aggregate_voters(d3_id)
        else:
            voters = []
            aggregated_voters = []
    else:
        parcels = [
                {'last_sale_amount': 13031.00,
                'last_sale_date': "2010-06-17",
                'vacant_percent': 50, # Check whether this is really stored as a percent or a ratio in the databse.
                'num_vacant': 3,
                'num_occupied': 3,
                'block_number': 'ITS-UI-LIKE',
                'prop_addr': '49 King',
                'city_name': 'Detroit',
                'prop_parcelnum': '01002779'}
                ] # Eventually provide some actual results in here for testing purposes.
        voters = [{'d3_year': 2019, 'voter_birth_year': 1944},
            {'d3_year': 2019, 'voter_birth_year': 1947},
            {'d3_year': 2019, 'voter_birth_year': 1947},
            {'d3_year': 2019, 'voter_birth_year': 1967},
            {'d3_year': 2019, 'voter_birth_year': 1967},
            {'d3_year': 2019, 'voter_birth_year': 1968},
            {'d3_year': 2019, 'voter_birth_year': 1968},
            {'d3_year': 2019, 'voter_birth_year': 1990}]
        aggregated_voters = []
        ownership = [{'year': 2019, 'owner_name': 'Jetson,George', 'owner_address': "019409013 Space Way, Satellite B87ZZ9"},
                {'year': 2009, 'owner_name': 'Bird,Big', 'owner_address': "123 Sesame St, New York, NY"}]
        demolitions = [{'demo_contractor': "Biff & Sully",
            'demo_price': "$123.58",
            'demo_funding_source': "The CvC Foundation",
            'demo_date': "07/18/2016",
            'demo_was_commercial': "No"}]
        vacancy = [{'d3_year': 2018,
            'quarter': "Q1",
            'vacant_percent': "33.3%",
            'num_vacant': 4,
            'num_occupied': 8}]

    voters = voters[::-1]
    current_year = datetime.now().year
    for voter in voters:
        voter['voter_age_by_years_end'] = current_year - voter['voter_birth_year']
    standard_voters = convert_to_standard_model(voters, ['d3_year', 'voter_age_by_years_end'])

    ownership_fields = ['year', 'owner_name', 'owner_address']
    ownership_display_name_by_field = {'year': "Year", 'owner_name': "Owner", 'owner_address': "Owner Address"}
    standard_ownership = convert_to_standard_model(ownership, ownership_fields)
    ownership_stacked = stack(ownership, ownership_display_name_by_field)
    ownership_vertical = {'data': ownership_stacked, 'fields': ownership_fields}

    demolitions_name_by_field = {'demo_contractor': "Contractor Name",
            'demo_price': "Price", # $###.##
            'demo_funding_source': "Funding Source",
            'demo_date': "Date", # MM/DD/YYYY
            'demo_was_commercial': "Commerical Demolition"} # Yes/No
    demolitions_stacked = stack(demolitions, demolitions_name_by_field)

    vacancy_name_by_field = OrderedDict([('d3_year', "Year"),
        ('quarter', "Quarter"),
        ('vacant_percent', "Percent Vacant"), # ##.#%
        ('num_vacant', "Number Vacant"),
        ('num_occupied', "Number Occupied")])
    vacancy_stacked = stack(vacancy, vacancy_name_by_field)

    data = { 'search_type': search_type,
            'search_term': search_term,
            'parcels': parcels,
            'json_parcels': json.dumps(parcels), # This is only here to be passed
            # back to weasy_pdf.py, avoiding further queries. If Django templating
            # supported something like the tojson filter, we could just use that
            # in the template ({{ parcels|tojson|safe }}) instead.
            'voters': standard_voters,
            'ownership': standard_ownership,
            'ownership_vertical': ownership_vertical,
            'demolitions': demolitions_stacked,
            'vacancy': vacancy_stacked,
            'aggregated_voters': aggregated_voters,
            'error_message': error_message,
            'output_format': 'html'
        }
    return JsonResponse(data)


class NewIndexView(View):

    def __init__(self):
        self.template_name = 'hipbone/ajax-index.html'
        self.msg = ''
        self.context = { 'parcels': [],
                'msg': self.msg,
                'error_message': '',
                'output_format': 'html'
            }

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('%s?next=%s' % ('/hipbone/login/', request.path))

        return render(request, self.template_name, self.context)

    # When relying on asynchronous requests, the index should not need
    # to field any POST requests.

    # HOWEVER, we could still implment it to support JavaScript-free
    # browsing.
    #def post(self, request, *args, **kwargs):
    #    if not request.user.is_authenticated:
    #        return redirect('%s?next=%s' % ('/hipbone/login/', request.path))

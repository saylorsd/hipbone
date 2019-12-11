from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.views.generic import View
from django.conf import settings

from .forms import LoginForm, AddressForm

import requests, json

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
    else:
        parcels = [
                {'last_sale_amount': 13031.00,
                'last_sale_date': "2010-06-17",
                'vacant_percent': 50, # Check whether this is really stored as a percent or a ratio in the databse.
                'num_vacant': 3,
                'num_occupied': 3,
                'block_number': 'ITS-UI-LIKE'}
                ] # Eventually provide some actual results in here for testing purposes.

    data = { 'search_type': search_type,
            'search_term': search_term,
            'parcels': parcels,
            'json_parcels': json.dumps(parcels), # This is only here to be passed
            # back to weasy_pdf.py, avoiding further queries. If Django templating
            # supported something like the tojson filter, we could just use that
            # in the template ({{ parcels|tojson|safe }}) instead.
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

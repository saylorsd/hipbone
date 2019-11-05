from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.views.generic import View
from django.conf import settings

from .forms import LoginForm, AddressForm

import requests, json

from .models import UserLoginActivity
from .tracking_util import save_activity
from .queries import query_db
from .parameters.local import PRODUCTION

from django.contrib.auth.decorators import login_required

from icecream import ic

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request, # Django 2.2
#            user = authenticate(          # Django 1.10
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
        self.msg = '(NOTE: This is currently using a WPRDC API to look up addresses.)'
        self.form_class = AddressForm
        self.parcel_id = None
        self.parcel_data = {}
        self.context = { 'parcel_id': self.parcel_id,
                'parcel_data': self.parcel_data,
                'parcels': [],
                'msg': self.msg,
                'error_message': ''
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
        address = None
        parcels = []
        if form.is_valid():
            # The form fields passed validation
            search_type = request.POST.get('search_type')
            if search_type == 'address':
                cd = form.cleaned_data
                address = cd['address']
                search_term = address
                url = "https://tools.wprdc.org/geo/geocode?addr={}".format(address)
            else:
                cd = form.cleaned_data
                parcel_id = cd['address'] # [ ] Generalize the term 'address' to some include parcel ID
                search_term = parcel_id
                url = "https://tools.wprdc.org/geo/reverse_geocode/?pin={}".format(parcel_id)

            if not PRODUCTION:
                response = requests.get(url)
                if response.status_code != 200:
                    error_message = 'Look-up failed with status code {}.'.format(response.status_code)
                else:
                    json_response = response.json()
                    if 'data' in json_response: # Parse results of address lookup
                        json_data = json_response['data']
                        if 'parcel_id' in json_data:
                            self.parcel_id = json_data['parcel_id']
                            parcel = {'parcel_id': json_data['parcel_id']}
                            if 'regions' in json_data and 'us_census_tract' in json_data['regions']:
                                if 'name' in json_data['regions']['us_census_tract']:
                                    self.parcel_data['Census tract'] = json_data['regions']['us_census_tract']['name']
                                    parcel['parcel_data'] = {'Census tract': json_data['regions']['us_census_tract']['name']}
                            parcels.append(parcel)

                    elif 'results' in json_response: # Parse results of parcel ID lookup
                        json_results = json_response['results']
                        self.parcel_id = parcel_id
                        parcel = {'parcel_id': parcel_id}
                        if 'us_census_tract' in json_results:
                            if 'name' in json_results['us_census_tract']:
                                self.parcel_data['Census tract'] = json_results['us_census_tract']['name']
                                parcel['parcel_data'] = {'Census tract': json_results['us_census_tract']['name']}
                        parcels.append(parcel)
            else:
                rows = query_db(search_type, search_term)
                parcels = []
                for row in rows:
                    parcel = {}
                    if search_type == 'address':
                        parcel['address'] = search_term
                    else:
                        parcel['parcel_id'] = search_term

                    parcel['parcel_data'] = {'Census tract': json.dumps(rows)}
                    parcels.append(parcel)

#            if search_type == 'address': # This is just for testing handling of multiple search results.
#                parcels.append({'parcel_id': '123 Sesame Street', 'parcel_data': {'Census tract': '1234567890', 'main import': 'Cookies!'}})

        self.context = { 'address_form': form,
                'search_type': search_type,
                'address': address if address is not None else None,
                'parcels': parcels,
                'parcel_id': self.parcel_id,
                'parcel_data': self.parcel_data,
                'msg': self.msg,
                'error_message': error_message
            }
        post_response = render(request, self.template_name, self.context)
        return post_response

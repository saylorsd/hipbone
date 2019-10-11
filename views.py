from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.views.generic import View
#from django_weasyprint import WeasyTemplateResponseMixin
from django.conf import settings

from .forms import LoginForm, AddressForm

import requests, json

from .models import UserLoginActivity
from .tracking_util import save_activity

from django.contrib.auth.decorators import login_required

#from icecream import ic

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
#            user = authenticate(request, # Django 2.2
            user = authenticate(          # Django 1.10
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
                'msg': self.msg
            }

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        self.context['address_form'] = form
        return render(request, self.template_name, self.context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            # The form fields passed validation
            cd = form.cleaned_data
            address = cd['address']
            url = "https://tools.wprdc.org/geo/geocode?addr={}".format(address)
            response = requests.get(url)
            json_response = response.json()
            if 'data' in json_response:
                json_data = json_response['data']
                if 'parcel_id' in json_data:
                    self.parcel_id = json_data['parcel_id']
                    if 'regions' in json_data and 'us_census_tract' in json_data['regions']:
                        if 'name' in json_data['regions']['us_census_tract']:
                            self.parcel_data['census_tract'] = json_data['regions']['us_census_tract']['name']

        self.context = { 'address_form': form,
                'parcel_id': self.parcel_id,
                'parcel_data': self.parcel_data,
                'msg': self.msg
            }
        post_response = render(request, self.template_name, self.context)
        return post_response


#class IndexPrintView(WeasyTemplateResponseMixin, IndexView):
#    # Output of IndexView rendered as PDF with hardcoded CSS
#    pdf_stylesheets = [
#        settings.STATIC_URL + 'css/housing-portal-basic-style.css',
#    ]
#    # Show PDF in-line (default: True, show download dialog)
#    pdf_attachment = False
#    # suggested filename (is required for attachment!)
#    pdf_filename = 'cookies.pdf'

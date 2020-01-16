from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.views.generic import View

from .forms import LoginForm, AddressForm

import requests, json
from datetime import datetime
from collections import OrderedDict

from .tracking_util import save_activity
from .queries import query_db, query_blight_violations, query_building_permits, query_demolitions, query_voters, query_ownership, query_parcel_tax_and_values, query_property_sales, aggregate_voters, query_d3_table
from .parameters.local import PRODUCTION

from icecream import ic

def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        next_page = request.POST.get('next')
        if next_page == '': # If the URL used for logging in has no next parameter,
            next_page = '/' # just default to redirecting to the root URL.
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request,
                                username=cd['username'],
                                password=cd['password'])
            if user is not None:
                if user.is_active:
                    login(request, user)
                    save_activity(request)
                    return HttpResponseRedirect(next_page)
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid login')
    else:
        form = LoginForm()
    return render(request, 'hipbone/login.html', {'form': form})

# BEGIN Table-formatting code #
def enumerated_row(row, fields):
    return {k: row[field] for k, field in enumerate(fields)}

def convert_to_standard_model(table, fields):
    """To simplify representation of data tables (making the JavaScript
    views simpler), convert the original table, which is in a
    list-of-dicts form, where the key for each field is a name,
    coming from the SQL query, hinting at the meaning of the field,
    to a different list-of-dicts form, where the keys are replaced by
    integers (0 through n-1, where n is the number of fields).

    This ensures that the JavaScript knows what order
    the fields should be in (since Python dicts do not by themselves
    preserve order)."""
    return [enumerated_row(row, fields) for row in table]

def stack(table, name_by_field):
    return [{0 : name, 1 : row[field]} for row in table for field, name in name_by_field.items()]

def group_by_record(table, name_by_field):
    return [[{0 : name, 1 : row[field]} for field, name in name_by_field.items()] for row in table]

def horizontalize_over_years(years, current_year):
    check_mark = "&#10003;"
    rows = []
    years_per_row = 12
    first_year = 2009
    while first_year <= current_year:
        last_year = min(current_year, first_year + years_per_row - 1)
        row1 = {}
        row2 = {}
        for k,year in enumerate(range(first_year, last_year + 1)):
            row1[k] = str(year) #str(year)[-2:] # Truncate year to last two digits.
            row2[k] = check_mark if year in years else "&nbsp;" # A non-breaking space is used
            # here to avoid the table row height collapsing.
        rows += [row1, row2]
        first_year += years_per_row
    return rows
# END Table-formatting code #

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
                    # Actually, in this case, we need to get all the d3_id values
                    # and use them all in subsequent queries.
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
        return JsonResponse({'error_message': "User is not logged in and therefore unable to get this data. Try the /login/ URL.",
            'reload': True })

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

    # Define fields and display-name lookup
    blight_violations_config = {'table_name': "blight_violations",
        'name_by_field': OrderedDict([("ticket_number", "Ticket Number"),
            ("agency_name", "Agency Name"),
            ("violator_name", "Violator Name"),
            ("violator_mailing_address", "Violator Mailing Address"),
            ("violation_date", "Violation Date"),
            ("violation_code_and_description", "Violation"), # Combine violation_code, violation_description like this f"{violation_code}: {violation_description}"
            ("disposition", "Disposition"),
            ("balance_due", "Balance Due")])
        }
    building_permits_config = {'table_name': "building_permits",
            'name_by_field': OrderedDict([("permit_no", "Permit Number"),
                ("permit_issued", "Permit Issued"),
                ("permit_completed", "Permit Completed"),
                ("permit_status", "Permit Status"),
                ("estimated_cost", "Estimated Cost"),
                ("bld_permit_type", "Permit Type"),
                ("bld_permit_desc", "Permit Description"),
                ("bld_type_use", "Building Use Type"),
                ("owner_name", "Owner"), # owner_first_name, owner_last_name ==> Display as (FIRST if exists) (LAST)
                ("owner_address", "Owner Address"), # [ ] Some comments on some of these building permit fields still need to be copied over from the specs.
                ("contractor_name", "Contractor Name")])
        }
    demolitions_config = {'table_name': 'demolitions',
        'name_by_field': OrderedDict([('demo_contractor', "Contractor Name"),
            ('demo_price', "Price"), # $###.##
            ('demo_funding_source', "Funding Source"),
            ('demo_date', "Date"), # MM/DD/YYYY
            ('demo_was_commercial', "Commerical Demolition")]) # Yes/No
        }

    foreclosures_config = {'table_name': 'tax_foreclosures',
        'name_by_field': OrderedDict([ ('year_foreclosed', "Year Foreclosed") ])
        }

    ownership_config = {'table_name': 'ownership',
        'name_by_field': OrderedDict([('d3_year', "Year"),
            ('owner_name', "Owner"),
            ('owner_address', "Owner Address")])
        }

    parcel_tax_and_values_config = {'table_name': 'parcel_tax_and_values',
        'name_by_field': OrderedDict([
            ('d3_year', "Year"),
            ('improved_value', "Improved Value"), # $###.##
            ('land_value', "Land Value"),
            ('pre', "PRE"),
            ('assessment_value', "Assessment Value"),
            ('taxable_value', "Taxable Value"),
            ('taxable_status', "Taxable Status")])
        }

    property_sales_config = {'table_name': 'property_sales',
        'name_by_field': OrderedDict([("sale_date", "Sale Date"),
            ("sale_price", "Sale Price"),
            ("grantor", "Grantor"),
            ("grantee", "Grantee"),
            ("sale_terms", "Sale Terms"),
            ("verified_by", "Verified By"),
            ("sale_instrument", "Sale Instrument")])
        }

    vacancy_config = {'table_name': 'vacancy',
        'name_by_field': OrderedDict([
            ('d3_year', "Year"),
            ('quarter', "Quarter"),
            ('vacant_percent', "Percent Vacant"), # ##.#%
            ('num_vacant', "Number Vacant"),
            ('num_occupied', "Number Occupied")])
        }

    if PRODUCTION:
        parcels = query_db(search_type, search_term)
        if len(parcels) > 0:
            d3_id = parcels[0]['d3_id']
            d3_ids = [p['d3_id'] for p in parcels]

            # Tables with records that contain single d3_id values
            building_permits = query_building_permits(building_permits_config, d3_ids)
            foreclosures = query_d3_table(foreclosures_config, d3_ids)
            foreclosures = [f['year_foreclosed'] for f in foreclosures]
            voters = query_voters(d3_ids)
            vacancy = query_d3_table(vacancy_config, d3_ids, 'ORDER BY d3_year DESC, quarter')
            ownership = query_ownership(d3_ids)
            parcel_tax_and_values = query_parcel_tax_and_values(d3_ids)
            property_sales = query_property_sales(d3_ids)

            # Tables with records that contain arrays of d3_id values
            blight_violations = query_blight_violations(blight_violations_config, d3_id)
            demolitions = query_demolitions(demolitions_config, d3_id)
        else:
            blight_violations = []
            building_permits = []
            demolitions = []
            foreclosures = []
            ownership = []
            parcel_tax_and_values = []
            property_sales = []
            vacancy = []
            voters = []
    else:
        parcels = [
                {
                'd3_id': '18',
                'census_tract_number': '03',
                'prop_addr': '49 King',
                'city_name': 'Detroit',
                'prop_parcelnum': '01002779',
                'y_wgs84': 42.38090737362023,
                'x_wgs84':-83.07919430958162
                }
                ]
        voters = [{'d3_year': 2019, 'voter_birth_year': 1944},
            {'d3_year': 2019, 'voter_birth_year': 1947},
            {'d3_year': 2019, 'voter_birth_year': 1947},
            {'d3_year': 2019, 'voter_birth_year': 1967},
            {'d3_year': 2019, 'voter_birth_year': 1967},
            {'d3_year': 2019, 'voter_birth_year': 1968},
            {'d3_year': 2019, 'voter_birth_year': 1968},
            {'d3_year': 2019, 'voter_birth_year': 1990}]
        ownership = [{'d3_year': 2019, 'owner_name': 'Jetson,George', 'owner_address': "019409013 Space Way, Satellite B87ZZ9"},
                {'d3_year': 2009, 'owner_name': 'Bird,Big', 'owner_address': "123 Sesame St, New York, NY"}]
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
        blight_violations = [{"ticket_number": "781-Y-TCN",
            "agency_name": "Nosiness Bureau",
            "violator_name": "Guy Smiley",
            "violator_mailing_address": "129 Sesame St, New York, NY, 10001-3823, USA, Earth",
            "violation_date": "01/01/2011",
            "violation_code_and_description": "408: Blighted teapot",
            "disposition": "Cracked",
            "balance_due": "$4.19"}]
        building_permits = [{"permit_no": "ICU71689",
            "permit_issued": "01/01/2018",
            "permit_completed": "02/02/2019",
            "permit_status": "Complete",
            "estimated_cost": "$78.13",
            "bld_permit_type": "Construction",
            "bld_permit_desc": "Building a tiny house",
            "bld_type_use": "Residential",
            "owner_name": "Little Bird",
            "owner_address": "123B Sesame Street, New York, NY",
            "contractor_name": "Biff"} ]

        foreclosures = [2009, 2012, 2020]
        parcel_tax_and_values = [{
            'd3_year': 2018,
            'improved_value': '$10,000.00',
            'land_value': '$3,000,000.00',
            'pre': 'LOBOT',
            'assessment_value': '$88,888.99',
            'taxable_value': '$89,000.00',
            'taxable_status': 'So Taxable'}]

        property_sales = [{"sale_date": "03/04/2010",
            "sale_price": "$101,010.10",
            "grantor": "Scrooge McDuck",
            "grantee": "Edward Slock",
            "sale_terms": " ",
            "verified_by": "Mr. E. Auditor",
            "sale_instrument": "Contract"}]

    voters = voters[::-1]
    current_year = datetime.now().year
    for voter in voters:
        voter['voter_age_by_years_end'] = current_year - voter['voter_birth_year']
    standard_voters = convert_to_standard_model(voters, ['d3_year', 'voter_age_by_years_end'])

    blight_violations_grouped = group_by_record(blight_violations, blight_violations_config['name_by_field'])
    building_permits_grouped = group_by_record(building_permits, building_permits_config['name_by_field'])
    demolitions_grouped = group_by_record(demolitions, demolitions_config['name_by_field'])
    ownership_grouped = group_by_record(ownership, ownership_config['name_by_field'])
    vacancy_grouped = group_by_record(vacancy, vacancy_config['name_by_field'])

    parcel_tax_and_values_grouped = group_by_record(parcel_tax_and_values, parcel_tax_and_values_config['name_by_field'])
    property_sales_grouped = group_by_record(property_sales, property_sales_config['name_by_field'])

    foreclosures_horizontal = horizontalize_over_years(foreclosures, current_year) # A possible
    # problem with this approach is that the JavaScript may not obtain the number of
    # columns from the base HTML template.

    data = { 'search_type': search_type,
            'search_term': search_term,
            'parcels': parcels,
            #'json_parcels': json.dumps(parcels), # This is only here to be passed
            # back to weasy_pdf.py, avoiding further queries. If Django templating
            # supported something like the tojson filter, we could just use that
            # in the template ({{ parcels|tojson|safe }}) instead.
                # json_parcels commented out since it was throwing an error pertaining
                # to a variable with type date being not JSON-serializable.
            'voters': standard_voters,

            'ownership_grouped': ownership_grouped,
            'demolitions_grouped': demolitions_grouped,
            'vacancy_grouped': vacancy_grouped,
            'blight_violations_grouped': blight_violations_grouped,
            'building_permits_grouped': building_permits_grouped,
            'tax_foreclosures': foreclosures_horizontal,
            'parcel_tax_and_values_grouped': parcel_tax_and_values_grouped,
            'property_sales_grouped': property_sales_grouped,
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

from django.db import connection
from icecream import ic

BASE_QUERY = """SELECT ST_X(mm.geom_centroid) x_wgs84,
    ST_Y(mm.geom_centroid) y_wgs84,
    mm.parcel_year,
    a1.prop_addr,
    a1.prop_parcelnum,
    a1.prop_legaldesc,
    a2.quarter,
    a2.vacant_percent,
    a2.num_vacant,
    a2.num_occupied,
    ptv.last_sale_amount,
    ptv.last_sale_date,
    db.block_number,
    dbg.block_group_name,
    c.city_name,
    ct.census_tract_number,
    mm.d3_id AS d3_id
    FROM parcel.master mm inner join parcel_admin_details a1 on mm.d3_id=a1.d3_id
    LEFT JOIN vacancy a2 on mm.d3_id=a2.d3_id
    LEFT JOIN parcel_tax_and_values ptv on mm.d3_id=ptv.d3_id
    LEFT JOIN dim_block db on mm.block_id=db.block_id
    LEFT JOIN dim_block_group dbg on mm.block_group_id=dbg.block_group_id
    LEFT JOIN dim_census_tract ct on mm.census_tract_id=ct.census_tract_id
    LEFT JOIN dim_city c on mm.city_id=c.city_id"""

def append_date_clause(query, date_str):
    if date_str is not None:
        query += " AND '{}'::date BETWEEN start_date AND end_date\nAND a2.quarter = EXTRACT(Quarter FROM '{}'::date);".format(date_str, date_str)
    return query

def dictfetchall(cursor):
    """Return all rows from a cursor as a dict. Set up the cursor by executing
    the query and then run this to get the result as a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def form_address_query(address, date_str=None):
    query = BASE_QUERY
    #--FUTURE TABLES LEFT JOIN HERE
    query += " WHERE prop_addr = UPPER('{}')".format(address)
    return append_date_clause(query, date_str)


def form_parcel_query(parcel_number, date_str=None):
    query = BASE_QUERY
    #--FUTURE TABLES LEFT JOIN HERE
    query += " WHERE prop_parcelnum = UPPER('{}')".format(parcel_number)
    return append_date_clause(query, date_str)

def query_db(search_type, search_term, date_str='9/1/2019'):
    if search_type == 'address':
        #sample_query = form_address_query('440 Burroughs', '9/1/2019')
        query = form_address_query(search_term, date_str)
    else: # search_type = 'parcel'
        query = form_parcel_query(search_term, date_str)

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = dictfetchall(cursor)
    return rows

def execute(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = dictfetchall(cursor)
    return rows

def aggregate_voters(d3_id):
    query = "SELECT d3_year, ROUND(voter_birth_year/10)*10::int AS decade, COUNT(id) AS count FROM voters WHERE d3_id = {} GROUP BY decade, d3_year ORDER BY d3_year, decade".format(d3_id)
    return execute(query)

def query_blight_violations(table_config, d3_id):
    """Query blight_violations table, using 'where {d3_id} = ANY(d3_id) to
    address the issue that in this table, the d3_id field is an
    array of bigints."""
    query = f"SELECT ticket_number, agency_name, violator_name, CONCAT(mailing_address_street_number, ' ', mailing_address_street_name, ', ', mailing_address_city, ', ', mailing_address_state, ' ', mailing_address_zip_code, ' ', mailing_address_nonusa_code, ' ', mailing_address_country) AS violator_mailing_address, violation_date, CONCAT(violation_code, ': ', violation_description) AS violation_code_and_description, disposition, balance_due::NUMERIC::MONEY FROM {table_config['table_name']} WHERE {d3_id} = ANY(d3_id) ORDER BY violation_date"
    return execute(query)

def query_building_permits(table_config, d3_id):
    query = f"SELECT permit_no, permit_issued, permit_completed, permit_status, estimated_cost::NUMERIC::MONEY, bld_permit_type, bld_permit_desc, bld_type_use, CONCAT_WS(' ', owner_first_name, owner_last_name) AS owner_name, CONCAT(CONCAT_WS(' ', owner_address1, owner_address2), ', ', owner_city, ', ', owner_state, ' ', owner_zip) as owner_address, CONCAT_WS(' ', contractor_first_name, contractor_last_name) AS contractor_name FROM {table_config['table_name']} WHERE {d3_id} = d3_id ORDER BY permit_issued"
    return execute(query)

def query_demolitions(table_config, d3_id):
    """Query demolitions table, using 'where {d3_id} = ANY(d3_id) to
    address the issue that in this table, the d3_id field is an
    array of bigints."""
    query = f"SELECT demo_contractor, demo_price::NUMERIC::MONEY, demo_funding_source, demo_timestamp AS demo_date, (CASE WHEN was_commercial IS NOT NULL THEN 'Yes' ELSE 'No' END) AS demo_was_commercial FROM {table_config['table_name']} WHERE {d3_id} = ANY(d3_id) ORDER BY demo_date"
    return execute(query)

def query_ownership(d3_id):
    query = "SELECT d3_year, CONCAT_WS('; ', owner_name, owner_name2) AS owner_name, CONCAT(owner_street_address, ', ', owner_city, ', ', owner_state, ' ', owner_zip_code, ' ', owner_country) AS owner_address FROM ownership WHERE d3_id = {} ORDER BY d3_year".format(d3_id)
    return execute(query)

def query_voters(d3_id):
    query = "SELECT d3_year, voter_birth_year FROM voters WHERE d3_id = {} ORDER BY d3_year, voter_birth_year".format(d3_id)
    # return execute(query)
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = dictfetchall(cursor)
    return rows

def query_d3_table(table_config, d3_ids):
    """This is a general querying function which takes all the fields specified in the table_config and
    selects them from the table named under the 'table_name' key of the table_config, filtering for
    a d3_id value among those in the passed list."""
    field_list = ', '.join(table_config['name_by_field'].keys())
    ids_sql_list = ', '.join([str(d3_id) for d3_id in d3_ids])
    query = f"SELECT {field_list} FROM {table_config['table_name']} WHERE d3_id IN ({ids_sql_list})" #ORDER BY d3_year"
    return execute(query)

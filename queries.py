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

def query_voters(d3_id):
    query = "SELECT d3_year, voter_birth_year FROM voters WHERE d3_id = {} ORDER BY d3_year, voter_birth_year".format(d3_id)
    # return execute(query)
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = dictfetchall(cursor)
    return rows

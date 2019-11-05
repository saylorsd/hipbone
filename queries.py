from django.db import connection, connections
from icecream import ic

def dictfetchall(cursor):
    """Return all rows from a cursor as a dict. Set up the cursor by executing 
    the query and then run this to get the result as a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def form_address_query(address, date_str=None):
    query = """SELECT ST_X(mm.geom_centroid) x_wgs84,
    ST_Y(mm.geom_centroid) y_wgs84,
    mm.parcel_year,
    a1.prop_addr,
    a1.prop_parcelnum,
    a1.prop_legaldesc,
    a2.quarter,
    a2.vacant_percent,
    a2.num_vacant,
    a2.num_occupied
    FROM parcel.master mm inner join parcel_admin_details a1 on mm.d3_id=a1.d3_id
    LEFT JOIN vacancy a2 on mm.d3_id=a2.d3_id"""

    #--FUTURE TABLES LEFT JOIN HERE
    query += " WHERE prop_addr = UPPER('{}')".format(address)

    if date_str is not None:
        query += " AND '{}'::date BETWEEN start_date AND end_date\nAND a2.quarter = EXTRACT(Quarter FROM '{}'::date);".format(date_str, date_str)
    return query

def query_db(search_type, search_term):
    if search_type == 'address':
        sample_query = form_address_query('440 Burroughs', '9/1/2019')
        query = sample_query
        #ic(query)
        #query = "SELECT * FROM parcel.master LIMIT 3;"
    #with connections['default'].cursor() as cursor:
    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = dictfetchall(cursor)
    return rows

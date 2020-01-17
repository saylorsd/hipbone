const CARTO_USER = 'wprdc';
const MAPS_API_ENDPOINT = `https://${CARTO_USER}.carto.com/api/v1/map`;


// get a better query for this
const CARTO_SQL =`SELECT min(cartodb_id) as id, min(the_geom) as the_geom, min(the_geom_webmercator) as the_geom_webmercator, d3_id, prop_addr, prop_parcelnum 
                    FROM wprdc.d3_parcels 
                    GROUP BY d3_id, prop_addr, prop_parcelnum`;

// todo: remove this eventually, i'm using this for a hack fix I have with matching parcel data.
const DEV = ['localhost', '127.0.0.1'].includes(window.location.hostname);

let dataMap, searchMap;

const mapSettings = {
    style: 'mapbox://styles/mapbox/streets-v11',
    center: [-83.07919430958162, 42.38090737362023],
    zoom: 16,
    interactive: true,
    minZoom: 12,
};

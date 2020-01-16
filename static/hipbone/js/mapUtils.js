const lineLayer = {
    id: 'parcel-lines',
    source: 'parcels',
    'source-layer': 'parcels',
    type: 'line',
    paint: {
        "line-width": {
            "stops": [
                [15, 1],
                [18, 2]
            ]
        },
        "line-color": "rgba(2, 2, 2, 1)",
        "line-opacity": {
            "stops": [
                [1, .1],
                [18, .3]
            ]
        }
    }
};

const fillLayer = {
    id: 'parcel-fill',
    source: 'parcels',
    'source-layer': 'parcels',
    type: 'fill',
    paint: {
        'fill-color': '#627BC1',
        'fill-opacity': 0.5
    }
};

const highlightLayer = {
    id: 'parcel-highlight',
    source: 'parcels',
    'source-layer': 'parcels',
    type: 'fill',
    paint: {
        'fill-color': '#272cc1',
        'fill-opacity': 1
    },
    filter: ['==', 'd3_id', '']
}


function cartoInstantiationParams(id, sql) {
    return {
        layers: [
            {
                id,
                options: {
                    sql,
                },
            },
        ],
    };
}

function extractCartoTileUrls(data) {
    return data.metadata.tilejson.vector.tiles;
}

const CARTO_USER = 'wprdc';
const MAPS_API_ENDPOINT = `https://${CARTO_USER}.carto.com/api/v1/map`;

function getConfig(id, sql) {
    return encodeURIComponent(
        JSON.stringify(cartoInstantiationParams(id, sql)),
    );
}

let map = null;

function getCartoSource(config) {
    return new Promise(function (resolve, reject) {
        fetch(`${MAPS_API_ENDPOINT}?config=${config}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        })
            .then(function (response) {
                return response.json();
            }, function (error) {
                return reject(error);
            })
            .then(
                function (data) {
                    resolve({
                        type: 'vector',
                        tiles: extractCartoTileUrls(data),
                        minzoom: 11
                    });
                },
                function (error) {
                    return reject(error);
                },
            );
    });
}

function setCartoSource(map, source) {
    map.addSource('parcels', source);
}

var hoveredStateId = null;
$(document).ready(function () {
        mapboxgl.accessToken = 'pk.eyJ1IjoibmVzc2JvdCIsImEiOiJjazU3NnNrb2MwMDcyM2pvNjYzM2hxbDdnIn0.Ip9ledWRI3KfL_FxAykCYA';
        map = new mapboxgl.Map({
            container: 'map',
            style: 'mapbox://styles/mapbox/streets-v11',
            center: [-83.0458333, 42.3313889],
            zoom: 16,
            interactive: false,
        });
        map.on('load', function () {
            // Get and set the source data
            // this involves querying carto to generate urls we can use to get tiles for our map
            // and then adding a mapbox source with those tiles
            const config = getConfig('parcels', 'SELECT * FROM wprdc.detroit_parcels');
            getCartoSource(config).then(
                function (data) {
                    // with the carto tiles in hand, we can now set our source and add our layers
                    setCartoSource(map, data);
                    map.addLayer(fillLayer);
                    map.addLayer(highlightLayer);
                    map.addLayer(lineLayer);
                },
                function (err) {
                    return console.error(err);
                }
            );
            map.resize();
            $('#map-tab-btn').on('click', function () {
                map.resize();
            })
        })

    }
);

function highlightParcel(parcelId, lng, lat) {
    map.setFilter('parcel-highlight', ['==', 'd3_id', parseInt(parcelId)]);
    map.setCenter([lng, lat]);
    map.setZoom(16);
}
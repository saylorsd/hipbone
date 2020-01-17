/**
 * Generate query params for carto tile request
 *
 * @param id - the id we want to give the map
 * @param sql - the query that carto uses to generate the map
 * @returns {{layers: [{options: {sql: *}, id: *}]}}
 */
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

/**
 * Generates config paramaters for a cart map tiles request
 *
 * @param id - the id we want to give the map
 * @param sql - the query that carto uses to generate the map
 * @returns {string}
 */
function getConfig(id, sql) {
    return encodeURIComponent(
        JSON.stringify(cartoInstantiationParams(id, sql)),
    );
}

/**
 * Extracts tile urls from carto response data.
 *
 * @param data - data returned from carto maps request
 * @returns [string]
 */
function extractCartoTileUrls(data) {
    return data.metadata.tilejson.vector.tiles;
}


/**
 * Sends a request to carto to generate tile urls for use in our mapbox sources
 * API docs: https://carto.com/developers/maps-api/reference/#operation/instantiateAnonymousMap
 *
 * @param config - config paramaters required by the maps api
 * @returns {Promise<unknown>}
 */
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
                        minzoom: 9
                    });
                },
                function (error) {
                    return reject(error);
                },
            );
    });
}

/**
 * Adds `source` as a source in `map`
 *
 * @param map {mapboxgl.Map} - mapboxgl map
 * @param source {Object} - mapbox source
 */
function setCartoSource(map, source) {
    map.addSource('parcels', source);
}


/**
 * Highlights a parcel on the map by seting a filter on the highlight layer.
 * If lng and lat are provided, also center and zoom the map at the position (lng, lat)
 *
 * @param map - mapboxgl map
 * @param parcelId - the parcelId of the parcel we'd like to highlight
 * @param lng? - longitude
 * @param lat? - latitude
 */
function highlightParcel(map, parcelId, lng, lat) {
    let searchParcelId = parcelId.slice(-1) === '.' ? parcelId : parcelId + '.';
    map.setFilter('parcel-highlight', ['==', 'prop_parcelnum', searchParcelId]);
    if (lng && lat) {
        map.setCenter([lng, lat]);
        map.setZoom(16);
    }
}


/**
 * Highlights the border of a parcel with id `parcelId`.
 * Used for highlighting the parcel the user is hovered over
 *
 * @param map - mapboxgl map
 * @param parcelId - parcel ID
 */
function highlightBorder(map, parcelId) {
    map.setFilter('parcel-hover', ['==', 'prop_parcelnum', parcelId]);
}

/**
 * Generates a function for use in callbacks to show a popup over a hovered parcel.
 *
 * @param map - mapboxgl map
 * @param curPopup - mapboxgl popup
 * @returns {function(...[*]=)}
 */
function showPopup(map, curPopup) {
    return function (e) {
        if (e.features.length) {
            let feature = e.features[0];
            map.getCanvas().style.cursor = 'pointer';

            highlightBorder(map, feature.properties.prop_parcelnum);

            curPopup.setLngLat(e.lngLat)
                .setHTML('<h4>' + feature.properties.prop_addr + '</h4>')
                .addTo(map)

        } else {
            hidePopup(map, curPopup);
        }
    }
}

/**
 * Generates a function for use in callbacks to hide a popup.
 *
 * @param map - mapboxgl map
 * @param curPopup - mapboxgl popup
 * @returns {function(...[*]=)}
 */
function hidePopup(map, curPopup) {
    return function () {
        map.getCanvas().style.cursor = 'grab';
        curPopup.remove();
    }
}

/**
 * Allows the map `map` to search for parcels on click.
 * @param map - mapboxgl map
 */
function attachClickSearchToMap(map) {
    map.on('click', 'parcel-fill', function (e) {
        if (e.features.length) {
            let feature = e.features[0];
            // search by parcel id
            $.ajax({
                url: '/ajax/get_parcels/',
                data: {
                    parcel_search_term: feature.properties.prop_parcelnum,
                    search_type: 'parcel'
                },
                dataType: 'json',
                success: handleResponseData
            });
            // highlight it on the map
            highlightParcel(map, feature.properties.prop_parcelnum)

        }

    })
}


/**
 * Creates a new mapboxgl map.  Applies functions in func on the map
 * @param mapDiv - the div to attach the generated map
 * @param funcs {[function({mapboxgl.Map}, ...)]} - array of functions ot apply to the map
 * @returns {mapboxgl.Map}
 */
function instantiateMap(mapDiv, funcs = []) {
    let map = new mapboxgl.Map({...mapSettings, container: mapDiv});
    let popup = new mapboxgl.Popup({closeOnClick: false});
    map.on('load', function () {
        // Get and set the source data
        // this involves querying carto to generate urls we can use to get tiles for our map
        // and then adding a mapbox source with those tiles
        const config = getConfig('parcels', CARTO_SQL);
        getCartoSource(config).then(
            function (data) {
                // with the carto tiles in hand, we can now set our source and add our layers
                setCartoSource(map, data);
                map.addLayer(fillLayer);
                map.addLayer(highlightLayer);
                map.addLayer(lineLayer);
                map.addLayer(hoverLayer);
                map.on('click', 'parcel-fill', function (e) {
                    console.log(e, e.features)
                });
                map.on('mousemove', 'parcel-fill', showPopup(map, popup));
                map.on('mouseleave', 'parcel-fill', hidePopup(map, popup));
            },
            function (err) {
                return console.error(err);
            }
        );
        map.resize();

        $('#map-tab-btn').on('click', function () {
            map.resize();
        })
    });
    funcs.map(func => func(map))
    return map;
}
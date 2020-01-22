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

const hoverLayer = {
    id: 'parcel-hover',
    source: 'parcels',
    'source-layer': 'parcels',
    type: 'line',
    paint: {
        "line-width": {
            "stops": [
                [15, 2],
                [18, 4]
            ]
        },
        "line-color": "rgba(2, 2, 2, 1)",
        "line-opacity": 1,
    },
    filter: ['==', 'prop_parcelnum', '']

};

const fillLayer = {
    id: 'parcel-fill',
    source: 'parcels',
    'source-layer': 'parcels',
    type: 'fill',
    paint: {
        'fill-color': '#4C8EB4',
        'fill-opacity': 0.2
    }
};

const highlightLayer = {
    id: 'parcel-highlight',
    source: 'parcels',
    'source-layer': 'parcels',
    type: 'fill',
    paint: {
        'fill-color': '#58BFAC',
        'fill-opacity': 0.5
    },
    filter: ['==', 'prop_parcelnum', '']
};

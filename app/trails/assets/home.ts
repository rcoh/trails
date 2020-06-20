import mapboxgl from 'mapbox-gl';
mapboxgl.accessToken = 'pk.eyJ1IjoiZXZlcnlzaW5nbGV0cmFpbCIsImEiOiJja2JsNmV2YjcwaWY5MnFxbmdtanF4aGUyIn0.ioFGm3P5s1kOpv7fJerp7g';

export const setupMap = (center: any, perimeter: any) => {
    const map = new mapboxgl.Map({
        container: 'map',
        style: 'mapbox://styles/mapbox/streets-v11',
        center: center,
        zoom: 13
    });

    map.on('load', function() {
        map.addSource('park', {
            "type": 'geojson',
            'data': perimeter
        });
        map.addLayer({
            'id': 'park',
            'type': 'line',
            'source': 'park',
            'layout': {
            'line-join': 'round',
            'line-cap': 'round'
        },
        'paint': {
            'line-color': '#888',
            'line-width': 3
        }
        });
    });
}

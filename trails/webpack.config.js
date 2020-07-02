const path = require('path');
const BundleTracker = require('webpack-bundle-tracker')

module.exports = {
  entry: './assets/home.ts',
  //context: __dirname,
  externals: {
    'mapbox-gl': 'mapboxgl',
    'mapbox-gl-geocoder': 'MapboxGeocoder'
  },
  devtool: 'inline-source-map',
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
      },
    ],
  },
  resolve: {
    extensions: [ '.tsx', '.ts', '.js' ],
  },
  output: {
      path: path.resolve('./assets/bundles/'),
      filename: "[name]-[hash].js",
  },
  plugins: [
    new BundleTracker({filename: './webpack-stats.json'})
  ]
};

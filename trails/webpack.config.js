const path = require('path');
const BundleTracker = require('webpack-bundle-tracker')

module.exports = {
  entry: './ts/home.tsx',
  //context: __dirname,
  externals: {
    'mapbox-gl': 'mapboxgl',
    'mapbox-gl-geocoder': 'MapboxGeocoder',
    'react': 'React',
    'react-dom': 'ReactDOM',
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

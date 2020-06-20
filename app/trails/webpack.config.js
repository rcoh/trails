const path = require('path');
const BundleTracker = require('webpack-bundle-tracker')

module.exports = {
  entry: './assets/home.ts',
  //context: __dirname,
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
      library: 'Lib',
      path: path.resolve('./assets/bundles/'),
      filename: "[name]-[hash].js",
  },
  plugins: [
    new BundleTracker({filename: './webpack-stats.json'})
  ]
};

const path = require('path');

module.exports = {
    entry: './js/sync_subnets.js',
    output: {
        filename: 'bundle.js',
        path: path.resolve(__dirname, '../static/dist'),
    },
    module: {
        rules: [
            {
                test: /\.css$/i,
                use: ['style-loader', 'css-loader'],
            },
        ],
    },
};
(function () {
    function WeatherSymbolChooser(html) {
        this.html = html;
    }

    WeatherSymbolChooser.prototype.render = function (placeholder, name, id, initialState) {
        const html = this.html.replace(/__NAME__/g, name).replace(/__ID__/g, id);
        placeholder.outerHTML = html;

        const symbolChooser = new WeatherSymbolChooserWidget(id);
        symbolChooser.setState(initialState);
        return symbolChooser;
    };

    window.telepath.register('forecastmanager.widgets.WeatherSymbolChooser', WeatherSymbolChooser);
})();
class WeatherSymbolChooserWidgetController extends window.StimulusModule.Controller {
    connect() {
        const options = JSON.parse(this.element.dataset.options);
        new WeatherSymbolChooserWidget(this.element.id, options);
    }
}

window.wagtail.app.register('weather-symbol-chooser-widget', WeatherSymbolChooserWidgetController);
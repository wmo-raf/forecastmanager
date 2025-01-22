class DataParameterWidgetController extends window.StimulusModule.Controller {
    connect() {
        new DataParameterWidget(this.element.id, this.element.value);
    }
}

window.wagtail.app.register('data-parameter-widget', DataParameterWidgetController);
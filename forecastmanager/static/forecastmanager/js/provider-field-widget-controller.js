class ProviderFieldWidgetController extends window.StimulusModule.Controller {
    connect() {
        new ProviderFieldWidget(this.element.id, this.element.value);
    }
}

window.wagtail.app.register('provider-field-widget', ProviderFieldWidgetController);

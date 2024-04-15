function DataParameterWidget(id, initialValue) {
    const inputId = '#' + id
    this.input = $(inputId);

    const parameterListSelectId = id + "_parameter_list"
    this.parameterListSelectInput = $("#" + parameterListSelectId);

    const useKnownParameterInputId = id.split("-parameter")[0] + "-use_known_parameters"
    this.checkIsKnownParameterInput = $("#" + useKnownParameterInputId)

    const that = this

    this.checkIsKnownParameterInput.change(function () {
        const checked = $(this).is(":checked")

        if (checked) {
            that.input.hide()
            that.parameterListSelectInput.show()
        } else {
            that.input.show()
            that.parameterListSelectInput.hide()
        }

    })

    if (this.checkIsKnownParameterInput.is(":checked")) {
        // clear any previous value
        that.parameterListSelectInput.show()
    } else {
        that.input.show()
    }

    this.parameterListSelectInput.change(function () {
        const selectedVal = $(this).val()
        that.setState(selectedVal)
    })
}

DataParameterWidget.prototype.setState = function (newState) {
    this.input.val(newState);
};

DataParameterWidget.prototype.getState = function () {
    return this.input.val();
};

DataParameterWidget.prototype.getValue = function () {
    return this.input.val();
};

DataParameterWidget.prototype.focus = function () {
}
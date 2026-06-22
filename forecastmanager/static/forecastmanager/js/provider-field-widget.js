function ProviderFieldWidget(id, initialValue) {
    const inputId = '#' + id;
    this.input = $(inputId);

    const fieldListSelectId = id + "_field_list";
    this.fieldListSelect = $("#" + fieldListSelectId);

    // The sibling provider <select> lives in the same inline form row. Its id is
    // the source_field id with the trailing "-source_field" swapped for "-provider".
    const providerInputId = id.replace(/-source_field$/, "-provider");
    this.providerSelect = $("#" + providerInputId);

    // Keep a pristine copy of every option so we can re-filter repeatedly.
    this.allOptions = this.fieldListSelect.find("option").map(function () {
        return {
            value: $(this).val(),
            label: $(this).text(),
            provider: $(this).attr("data-provider") || "",
        };
    }).get();

    const that = this;

    this.providerSelect.on("change", function () {
        that.filterByProvider($(this).val(), true);
    });

    this.fieldListSelect.on("change", function () {
        that.setState($(this).val());
    });

    // Initial render: filter to the currently selected provider, preserving the
    // stored value when it still belongs to that provider.
    this.filterByProvider(this.providerSelect.val(), false);
}

ProviderFieldWidget.prototype.filterByProvider = function (provider, resetWhenMismatch) {
    const current = this.input.val();
    const select = this.fieldListSelect;
    select.empty();
    select.append($("<option></option>").attr("value", "").text("-----------"));

    let keepCurrent = false;
    this.allOptions.forEach(function (opt) {
        if (!opt.value) {
            return; // skip the placeholder, already added
        }
        if (!provider || opt.provider === provider) {
            const optionEl = $("<option></option>")
                .attr("value", opt.value)
                .attr("data-provider", opt.provider)
                .text(opt.label);
            if (opt.value === current) {
                optionEl.attr("selected", "selected");
                keepCurrent = true;
            }
            select.append(optionEl);
        }
    });

    if (keepCurrent) {
        select.val(current);
    } else if (resetWhenMismatch) {
        select.val("");
        this.setState("");
    }
};

ProviderFieldWidget.prototype.setState = function (newState) {
    this.input.val(newState);
};

ProviderFieldWidget.prototype.getState = function () {
    return this.input.val();
};

ProviderFieldWidget.prototype.getValue = function () {
    return this.input.val();
};

ProviderFieldWidget.prototype.focus = function () {
};

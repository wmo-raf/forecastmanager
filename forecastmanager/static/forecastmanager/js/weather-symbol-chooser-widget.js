function WeatherSymbolChooserWidget(id, symbol_options) {
    /*
    id = the ID of the HTML element where icon input should be attached
    */

    this.symbolOptions = symbol_options
    this.iconInput = $('#' + id);
    this.iconContainer = $("#" + id + "-icon-container")
    this.initialRender = true

    this.modalTrigger = $("#" + id + "-modal-trigger")
    this.modalTrigger.on("click", () => {
        this.createIconOptions()
        if (this.modalContainer) {
            this.modalContainer.modal("show")
        }
    })

    this.iconClear = $("#" + id + "-icon-choice-clear")
    this.iconClear.on("click", this.handleSelectedIconClear.bind(this))
}


WeatherSymbolChooserWidget.prototype.setState = function (newState) {
    this.iconInput.val(newState);
    // show initially selected
    if (this.initialRender) {
        this.initialRender = false
        if (newState) {
            const symbol = this.symbolOptions.find((s) => s.value === newState)
            if (symbol) {
                const imgMarkup = this.createIconImgMarkup(symbol)
                this.iconContainer.html(imgMarkup)
                this.iconClear.show()
            }
        }
    }
};

WeatherSymbolChooserWidget.prototype.getState = function () {
    return this.iconInput.val();
};

WeatherSymbolChooserWidget.prototype.getValue = function () {
    return this.iconInput.val();
};

WeatherSymbolChooserWidget.prototype.focus = function () {
    this.iconInput.focus();
}

WeatherSymbolChooserWidget.prototype.createIconOptions = function () {
    const that = this
    $('body > .modal').remove();
    this.modalContainer = $(`<div class="modal fade" tabindex="-1" role="dialog" aria-hidden="true">
                                <div class="modal-dialog"><div class="modal-content">
                                    <button type="button" class="button close button--icon text-replace" data-dismiss="modal">
                                    <svg class="icon icon-cross" aria-hidden="true"><use href="#icon-cross"></use></svg>
                                        Close
                                    </button>
                                    <div class="modal-body">
                                        <header class="w-header w-header--hasform">
                                            <div class="row">
                                                <div class="left">
                                                    <div class="col">
                                                        <h1 class="w-header__title" id="header-title">
                                                            <svg class="icon icon-doc-empty-inverse w-header__glyph" aria-hidden="true">
                                                                <use href="#icon-doc-empty-inverse"></use>
                                                            </svg>
                                                            Choose symbol
                                                        </h1>
                                                    </div>
                                                        <div class="w-field__wrapper w-mb-0 -w-mt-2.5" data-field-wrapper="">
                                                            <label class="w-field__label w-sr-only" htmlFor="id_icon_modal_filter" id="id_q-label">
                                                                Search
                                                            </label>
                                                            <div class="w-field w-field--char_field w-field--text_input">
                                                                <div class="w-field__input" data-field-input="">
                                                                    <svg class="icon icon-search w-field__icon" aria-hidden="true">
                                                                        <use href="#icon-search"></use>
                                                                    </svg>
                                                                    <input type="text" name="q" placeholder="Search" id="id_icon_modal_filter">
                                                                </div>
                                                            </div>
                                                        </div>
                                                </div>
                                            </div>
                                        </header>
                                        <div class="modal-icons-content"></div>
                                    </div>
                                </div>
                            </div>
                        </div>`);

    $('body').append(this.modalContainer);
    this.modalContainer.modal('hide');


    this.modalContainer.on('hidden.bs.modal', function () {
        that.modalContainer.remove();
    });

    this.modalIconsContent = this.modalContainer.find('.modal-icons-content');

    this.symbolOptions.forEach((symbol) => {
        const $container = $("<div class='symbol-container'>")
        $container.on("click", () => that.onIconSelect(symbol))
        $(`<div class="icon icon-option" aria-hidden="true"><img alt="${symbol.label}" src="${symbol.icon_url}"/></div>`).appendTo($container)
        $(`<div class="icon-label">${symbol.label}</div>`).appendTo($container)
        $container.appendTo(that.modalIconsContent)

    });


    this.iconModalFilter = $("#id_icon_modal_filter")
    this.iconModalFilter.on('keyup', this.handleIconListFilter.bind(this));
}

WeatherSymbolChooserWidget.prototype.onIconSelect = function (symbol) {
    const imgMarkup = this.createIconImgMarkup(symbol)
    this.iconContainer.html(imgMarkup)
    this.setState(symbol.value)

    if (this.modalContainer) {
        // close modal
        this.modalContainer.modal("hide")
    }
    // show clear button
    this.iconClear.show()
}

WeatherSymbolChooserWidget.prototype.createIconImgMarkup = function (symbol) {
    return $(`<div class="icon selected-icon" aria-hidden="true"><img alt="${symbol.label}" src="${symbol.icon_url}"/></div>`)
}


WeatherSymbolChooserWidget.prototype.handleIconListFilter = function (e) {
    const value = e.target.value
    this.modalIconsContent.find(".symbol-container").filter(function () {
        const $iconLabel = $(this).find(".icon-label")
        $(this).toggle($iconLabel.text().toLowerCase().indexOf(value) > -1)
    });
}


WeatherSymbolChooserWidget.prototype.handleSelectedIconClear = function () {
    // clear input value
    this.setState("")
    // clear displayed icon
    this.iconContainer.html("")
    // hide clear button
    this.iconClear.hide()
}








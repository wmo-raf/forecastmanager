const debounce = (callback, wait) => {
    let timeoutId = null;
    return (...args) => {
        window.clearTimeout(timeoutId);
        timeoutId = window.setTimeout(() => {
            callback.apply(null, args);
        }, wait);
    };
}

const bulmaHead = (id, idMenu, api, onSelect, delay, minLen = 2) => {
    const input = document.getElementById(id)
    const menuEl = document.getElementById(idMenu)
    menuEl.innerHTML = '<div class="dropdown-content"></div>'

    const setValue = e => {
        e.preventDefault()
        const label = e.target.text
        const value = e.target.dataset.value
        input.value = label
        menuEl.style.display = 'none'
        if (onSelect) {
            onSelect({label, value})
        }
        return false
    }

    const handleApi = e => {
        const value = e.target.value
        menuEl.style.display = 'none'
        menuEl.innerHTML = '<div class="dropdown-content"></div>'
        if (value.length <= minLen) {
            return
        }

        api(value).then(suggestions => {
            const suggestionsEl = suggestions.map(({label, value}) => {
                const a = document.createElement('a')
                a.href = '#'
                a.classList.add('dropdown-item')
                a.innerHTML = label
                a.dataset.value = value
                a.addEventListener('click', setValue)
                return a
            })

            suggestionsEl.map(suggEl => {
                menuEl.childNodes[0].appendChild(suggEl)
            })

            if (suggestions.length > 0) {
                menuEl.style.display = 'block'
            }

            if (suggestions.length === 0) {
                const div = document.createElement('div')
                div.classList.add('dropdown-item')
                div.innerHTML = 'No result'
                menuEl.childNodes[0].appendChild(div)

                menuEl.style.display = 'block'
            }
        })
    }
    input.addEventListener('input', debounce(handleApi, delay))

    input.addEventListener('focusout', e => {
        if (e.relatedTarget === null || !e.relatedTarget.classList.contains('dropdown-item')) {
            menuEl.style.display = 'none'
        }
    })

    input.addEventListener('focusin', handleApi)
}

window.bulmaHead = bulmaHead
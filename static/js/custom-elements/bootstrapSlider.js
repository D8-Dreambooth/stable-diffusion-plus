class BootstrapSlider {
    constructor(parentElement, options) {
        this.onChangeCallbacks = [];
        this.parentElement = parentElement;
        this.parentElement.classList.add("bootstrapSlider");

        this.min = (options.hasOwnProperty("min")) ? (Number.isInteger(options.min) ? options.min : parseFloat(options.min)) : 1;
        this.max = (options.hasOwnProperty("max")) ? (Number.isInteger(options.max) ? options.max : parseFloat(options.max)) : 150;
        this.step = (options.hasOwnProperty("step")) ? (Number.isInteger(options.step) ? options.step : parseFloat(options.step)) : 1;
        this.value = (options.hasOwnProperty("value")) ? (Number.isInteger(options.value) ? options.value : parseFloat(options.value)) : this.min;

        this.visible = (options.hasOwnProperty("visible")) ? options.visible : true;
        this.interactive = (options.hasOwnProperty("interactive")) ? options.interactive : true;
        this.label = (options.hasOwnProperty("label")) ? options.label : "";
        this.elem_id = parentElement.id;

        // create the HTML elements
        this.container = document.createElement("div");
        this.container.id = this.elem_id + "_container";

        this.labelWrapper = document.createElement("div");
        this.labelText = document.createElement("label");
        this.labelText.setAttribute("for", this.elem_id + "_number");
        this.labelText.classList.add("text-gray-500", "mb-1");
        this.labelText.title = options.title || "How many times to improve the generated image iteratively; higher values take longer; very low values can produce bad results";
        this.labelText.innerText = this.label;

        this.labelWrapper.appendChild(this.labelText);
        this.container.appendChild(this.labelWrapper);

        this.inputWrap = document.createElement("div");
        this.inputWrap.classList.add("input-group", "borderSection-sm");
        this.container.appendChild(this.inputWrap);

        this.rangeInput = document.createElement("input");
        this.rangeInput.type = "range";
        this.rangeInput.id = this.elem_id + "_range";
        this.rangeInput.classList.add("col-6", "col-lg-8", "disabled:cursor-not-allowed");
        this.rangeInput.min = this.min;
        this.rangeInput.max = this.max;
        this.rangeInput.step = this.step;
        this.rangeInput.value = this.value;
        if (!this.interactive) {
            this.rangeInput.disabled = true;
        }
        this.inputWrap.appendChild(this.rangeInput);
        this.numberInput = document.createElement("input");
        this.numberInput.type = "number";
        this.numberInput.id = this.elem_id + "_number";
        this.numberInput.classList.add("gr-box", "gr-input", "gr-text-input", "text-center", "h-6", "col-6", "col-lg-4");
        this.numberInput.min = this.min;
        this.numberInput.max = this.max;
        this.numberInput.step = this.step;
        this.numberInput.value = this.value;
        this.inputWrap.appendChild(this.numberInput);

        if (!this.visible) {
            this.container.style.display = "none";

        }
        this.rangeInput.addEventListener("input", (event) => {
            let value = parseInt(event.target.value, 10);
            if (this.step < 1) {
                value = parseFloat(event.target.value);
            }
            this.numberInput.value = value;
            for (let i = 0; i < this.onChangeCallbacks.length; i++) {
                this.onChangeCallbacks[i](value);
            }

        });

        this.numberInput.addEventListener("input", (event) => {
            let value = parseInt(event.target.value, 10);
            if (this.step < 1) {
                value = parseFloat(event.target.value);
            }
            this.rangeInput.value = String(value);
            for (let i = 0; i < this.onChangeCallbacks.length; i++) {
                this.onChangeCallbacks[i](value);
            }
        });
        this.updateValue = this.updateValue.bind(this);
        this.getValue = this.getValue.bind(this);
        this.setValue = this.setValue.bind(this);
        this.setOnChange = this.setOnChange.bind(this);
        this.show = this.show.bind(this);
        this.hide = this.hide.bind(this);
        this.setMin = this.setMin.bind(this);
        this.setMax = this.setMax.bind(this);
        this.setStep = this.setStep.bind(this);
        this.setOnChange(this.updateValue);
        parentElement.appendChild(this.container);
    }

    updateValue(newValue) {
        this.value = newValue;
        this.numberInput.value = this.value;
        this.rangeInput.value = this.value;
    }

    setMin(value) {
        this.min = value;
        this.numberInput.min = value;
        this.rangeInput.min = value;
    }

    setMax(value) {
        this.max = value;
        this.numberInput.max = value;
        this.rangeInput.max = value;
    }

    setStep(value) {
        this.step = value;
        this.numberInput.step = value;
        this.rangeInput.step = value;
    }

    setValue(value) {
        this.isProgrammaticUpdate = true;
        this.updateValue(value);
        this.isProgrammaticUpdate = false;
        this.parentElement.dataset.value = value;
    }

    setOnChange(callback) {
        this.onChangeCallbacks.push(callback);

    }

    show() {
        this.container.style.display = "";
    }

    hide() {
        this.container.style.display = "none";
    }

    getValue() {
        return this.value;
    }
}

$.fn.BootstrapSlider = function (inputOptions) {
    const defaultOptions = {
        min: 1,
        max: 150,
        step: 1,
        value: 150,
        visible: true,
        interactive: true,
        label: "Sampling steps"
    };

    this.each(function () {
        const $this = $(this);
        let slider = $this.data("BootstrapSlider");

        if (!slider) {
            const targetElement = this;
            const targetDataset = targetElement.dataset;

            const options = {
                ...defaultOptions,
                ...targetDataset,
                ...inputOptions
            };

            options.min = parseValue(options.min);
            options.max = parseValue(options.max);
            options.step = parseValue(options.step);
            options.value = parseValue(options.value, options.max);

            slider = new BootstrapSlider(targetElement, options);
            $this.data("BootstrapSlider", slider);
        }
    });

    return this.data("BootstrapSlider");
};

function parseValue(value, fallbackValue) {
    if (value === undefined) {
        return fallbackValue;
    }

    const parsedFloat = parseFloat(value);
    if (!Number.isNaN(parsedFloat)) {
        return parsedFloat;
    }

    const parsedInt = parseInt(value, 10);
    if (!Number.isNaN(parsedInt)) {
        return parsedInt;
    }

    return fallbackValue;
}



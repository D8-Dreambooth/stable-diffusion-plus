class BootstrapSlider {
    constructor(parentElement, options) {
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
        this.container.classList.add("gr-block", "gr-box", "relative", "w-full", "border-solid", "border", "border-gray-200", "gr-padded");

        this.wrap = document.createElement("div");
        this.wrap.classList.add("wrap", "svelte-5usjvi", "inset-0", "opacity-0");
        this.container.appendChild(this.wrap);

        this.inputWrapper = document.createElement("div");
        this.inputWrapper.classList.add("w-full", "flex", "flex-col");
        this.container.appendChild(this.inputWrapper);

        this.labelWrapper = document.createElement("div");
        this.labelWrapper.classList.add("row");
        this.inputWrapper.appendChild(this.labelWrapper);

        this.labelElement = document.createElement("div");
        this.labelElement.classList.add("col-9");
        this.labelWrapper.appendChild(this.labelElement);

        this.labelText = document.createElement("span");
        this.labelText.setAttribute("for", this.elem_id + "_number");
        this.labelText.classList.add("text-gray-500", "mb-2", "col-11", "fit");
        this.labelText.title = options.title || "How many times to improve the generated image iteratively; higher values take longer; very low values can produce bad results";
        this.labelText.innerText = this.label;
        let labelWrap = document.createElement("div");
        labelWrap.appendChild(this.labelText);
        this.labelElement.appendChild(labelWrap);

        this.numberInput = document.createElement("input");
        this.numberInput.type = "number";
        this.numberInput.id = this.elem_id + "_number";
        this.numberInput.classList.add("gr-box", "gr-input", "gr-text-input", "text-center", "h-6", "col-3");
        this.numberInput.min = this.min;
        this.numberInput.max = this.max;
        this.numberInput.step = this.step;
        this.numberInput.value = this.value;
        this.labelWrapper.appendChild(this.numberInput);

        this.rangeInput = document.createElement("input");
        this.rangeInput.type = "range";
        this.rangeInput.id = this.elem_id + "_range";
        this.rangeInput.classList.add("w-full", "disabled:cursor-not-allowed");
        this.rangeInput.min = this.min;
        this.rangeInput.max = this.max;
        this.rangeInput.step = this.step;
        this.rangeInput.value = this.value;
        if (!this.interactive) {
            this.rangeInput.disabled = true;
        }

        this.isProgrammaticUpdate = false;

        this.container.appendChild(this.rangeInput);

        if (!this.visible) {
            this.container.style.display = "none";

        }
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
        this.onChangeCallback = callback;
        this.rangeInput.addEventListener("input", (event) => {
            let value = parseInt(event.target.value, 10);
            if (this.step < 1) {
                value = parseFloat(event.target.value);
            }
            this.numberInput.value = value;
            if (this.onChangeCallback) {
                this.onChangeCallback(value);
            }
        });

        this.numberInput.addEventListener("input", (event) => {
            let value = parseInt(event.target.value, 10);
            if (this.step < 1) {
                value = parseFloat(event.target.value);
            }
            this.rangeInput.value = String(value);
            if (this.onChangeCallback) {
                this.onChangeCallback(value);
            }
        });
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



class BootstrapSlider {
    constructor(parentElement, options) {

        this.min = (options.hasOwnProperty("min")) ? (Number.isInteger(options.min) ? options.min : parseFloat(options.min)) : 1;
        this.max = (options.hasOwnProperty("max")) ? (Number.isInteger(options.max) ? options.max : parseFloat(options.max)) : 150;
        this.step = (options.hasOwnProperty("step")) ? (Number.isInteger(options.step) ? options.step : parseFloat(options.step)) : 1;
        this.value = (options.hasOwnProperty("value")) ? (Number.isInteger(options.value) ? options.value : parseFloat(options.value)) : this.min;

        this.visible = (options.hasOwnProperty("visible")) ? options.visible : true;
        this.interactive = (options.hasOwnProperty("interactive")) ? options.interactive : true;
        this.label = (options.hasOwnProperty("label")) ? options.label : "";
        this.elem_id = (options.hasOwnProperty("elem_id")) ? options.elem_id : "item-" + generateRandomString(8);

        // create the HTML elements
        this.container = document.createElement("div");
        this.container.id = this.elem_id;
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
        this.labelText.classList.add("text-gray-500", "mb-2", "col-11", "fit");
        this.labelText.title = options.title || "How many times to improve the generated image iteratively; higher values take longer; very low values can produce bad results";
        this.labelText.innerText = this.label;
        let labelWrap = document.createElement("div");
        labelWrap.appendChild(this.labelText);
        this.labelElement.appendChild(labelWrap);

        this.numberInput = document.createElement("input");
        this.numberInput.type = "number";
        this.numberInput.classList.add("gr-box", "gr-input", "gr-text-input", "text-center", "h-6", "col-3");
        this.numberInput.min = this.min;
        this.numberInput.max = this.max;
        this.numberInput.step = this.step;
        this.numberInput.value = this.value;
        this.numberInput.addEventListener("input", (event) => {
            this.updateValue(event.target.value);
        });
        this.labelWrapper.appendChild(this.numberInput);

        this.rangeInput = document.createElement("input");
        this.rangeInput.type = "range";
        this.rangeInput.id = "range_id_0";
        this.rangeInput.name = "wtf";
        this.rangeInput.classList.add("w-full", "disabled:cursor-not-allowed");
        this.rangeInput.min = this.min;
        this.rangeInput.max = this.max;
        this.rangeInput.step = this.step;
        this.rangeInput.value = this.value;
        if (!this.interactive) {
            this.rangeInput.disabled = true;
        }
        this.rangeInput.addEventListener("input", (event) => {
            this.updateValue(event.target.value);
        });
        this.container.appendChild(this.rangeInput);

        if (!this.visible) {
            this.container.style.display = "none";
        }
        parentElement.appendChild(this.container);
    }

    updateValue(newValue) {
        this.value = newValue;
        this.numberInput.value = this.value;
        this.rangeInput.value = this.value;
        if (this.onChangeCallback) {
            console.log("Callback?")
            this.onChangeCallback(this.value);
        }
    }


    setOnChange(callback) {
        console.log("Callback set...")
        this.onChangeCallback = callback;
        this.rangeInput.addEventListener("input", (event) => {
            const value = parseInt(event.target.value, 10);
            this.numberInput.value = String(value);
            if (this.onChangeCallback) {
                this.onChangeCallback(value);
            }
        });

        this.numberInput.addEventListener("input", (event) => {
            const value = parseInt(event.target.value, 10);
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

$.fn.BootstrapSlider = function () {
    const defaultOptions = {
        min: this.data.hasOwnProperty("min") ? (Number.isInteger(this.data["min"]) ? this.data["min"] : parseFloat(this.data["min"])) : 1,
        max: this.data.hasOwnProperty("max") ? (Number.isInteger(this.data["max"]) ? this.data["max"] : parseFloat(this.data["max"])) : 150,
        step: this.data.hasOwnProperty("step") ? (Number.isInteger(this.data["step"]) ? this.data["step"] : parseFloat(this.data["step"])) : 1,
        value: this.data.hasOwnProperty("value") ? (Number.isInteger(this.data["value"]) ? this.data["value"] : parseFloat(this.data["value"])) : this.data.hasOwnProperty("max") ? (Number.isInteger(this.data["max"]) ? this.data["max"] : parseFloat(this.data["max"])) : 150,
        visible: this.data.hasOwnProperty("visible") ? this.data["visible"] : true,
        interactive: this.data.hasOwnProperty("interactive") ? this.data["interactive"] : true,
        label: this.data.hasOwnProperty("label") ? this.data["label"] : "Sampling steps",
        elem_id: this.data.hasOwnProperty("elem-id") ? this.data["elem-id"] : "item-" + generateRandomString(8)
    };


    this.each(function () {
        const $this = $(this);
        let slider = $this.data("BootstrapSlider");

        if (!slider) {
            const options = {
                ...defaultOptions,
                ...$this.data(),
            };
            slider = new BootstrapSlider(this, options);
            $this.data("BootstrapSlider", slider);
        }
    });

    return this;
};


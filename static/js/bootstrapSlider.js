class BootstrapSlider {
    constructor(parentElement, options) {
        this.min = options.min || 1;
        this.max = options.max || 150;
        this.step = options.step || 1;
        this.value = options.value || this.min;
        this.visible = options.visible || true;
        this.interactive = options.interactive || true;
        this.label = options.label || "Sampling steps";
        this.elem_id = options.elem_id || "item-" + generateRandomString(8);

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
        this.labelWrapper.classList.add("flex", "justify-between");
        this.inputWrapper.appendChild(this.labelWrapper);

        this.labelElement = document.createElement("label");
        this.labelElement.htmlFor = "range_id_0";
        this.labelWrapper.appendChild(this.labelElement);

        this.labelText = document.createElement("span");
        this.labelText.classList.add("text-gray-500", "text-[0.855rem]", "mb-2", "block", "dark:text-gray-200", "relative", "z-40");
        this.labelText.title = options.title || "How many times to improve the generated image iteratively; higher values take longer; very low values can produce bad results";
        this.labelText.innerText = this.label;
        this.labelElement.appendChild(this.labelText);

        this.numberInput = document.createElement("input");
        this.numberInput.type = "number";
        this.numberInput.classList.add("gr-box", "gr-input", "gr-text-input", "text-center", "h-6");
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
        this.rangeInput.name = "cowbell";
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
        if (this.onChange) {
            this.onChange(this.value);
        }
    }

    getValue() {
        return this.value;
    }

    setOnChange(callback) {
        this.onChangeCallback = callback;
        this.rangeInput.addEventListener("input", (event) => {
            const value = parseInt(event.target.value, 10);
            this.numberInput.value = value;
            if (this.onChangeCallback) {
                this.onChangeCallback(value);
            }
        });

        this.numberInput.addEventListener("input", (event) => {
            const value = parseInt(event.target.value, 10);
            this.rangeInput.value = value;
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


}
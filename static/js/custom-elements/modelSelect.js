class ModelSelect {
    constructor(container, options) {
        registerSocketMethod(container, "reload_models", this.modelSocketUpdate.bind(this));
        this.container = container;
        this.model_type = options.model_type;
        this.ext_include = options.ext_include;
        this.ext_exclude = options.ext_exclude;
        this.multiple = options.multiple;
        this.load_on_select = options.load_on_select;
        this.modelList = [];
        this.onchangeCallbacks = [];

        // Set the default value(s)
        this.value = options.value || "none";

        // Create the select element
        this.selectElement = document.createElement("select");
        this.selectElement.classList.add("form-control");
        this.selectElement.classList.add("model-select");
        this.selectElement.dataset["key"] = options.key || container.id;
        this.selectElement.id = container.id + "_select";

        // Add the multiple attribute if specified
        if (this.multiple) {
            this.selectElement.setAttribute("multiple", "true");
        }

        // Add the class specified in the options, if any
        const addClass = options.addClass || "";
        if (addClass !== "") {
            if (addClass.indexOf(" ") !== -1) {
                const classes = addClass.split(" ");
                for (let i = 0; i < classes.length; i++) {
                    this.selectElement.classList.add(classes[i]);
                }
            } else {
                this.selectElement.classList.add(addClass);
            }
        }


        this.selectElement.onchange = () => {
            // Get the selected options from the select element
            const selectedOptions = Array.from(this.selectElement.options)
                .filter(option => option.selected && option.value !== "none");
            console.log("Selected: ", selectedOptions);
            if (selectedOptions.length > 0) {
                // Get the values of all the selected options
                const selectedValues = selectedOptions.map(option => option.value);
                if (this.multiple) {
                   this.value = selectedValues;
                } else {
                    this.value = selectedValues[0];
                }
                for (let i = 0; i < this.onchangeCallbacks.length; i++) {
                    console.log("Callback:", this.value);
                    this.onchangeCallbacks[i](this.value);
                }
            } else {
                this.value = "none";
            }
        }

        const labelElement = document.createElement("label");
        labelElement.setAttribute("for", this.selectElement.id);
        labelElement.textContent = options.label;
        labelElement.classList.add("form-label");

        const wrapper = document.createElement("div");
        wrapper.classList.add("form-group");
        wrapper.appendChild(labelElement);
        wrapper.appendChild(this.selectElement);
        this.container.appendChild(wrapper);

        this.getValue = this.getValue.bind(this);
        this.setValue = this.setValue.bind(this);
        this.refresh = this.refresh.bind(this);
        this.getModel = this.getModel.bind(this);
        this.refresh().then(() => {

        });
    }

    modelSocketUpdate(data) {
        const new_model = data.model_type;
        const to_load = data["to_load"];
        let modelTypes = [this.model_type];
        if (this.model_type.indexOf("_") !== -1) {
            modelTypes = this.model_type.split("_");
        }
        let doRefresh = false;
        for (let i = 0; i < modelTypes.length; i++) {
            if (modelTypes[i] === new_model) {
                doRefresh = true;
                break;
            }
        }
        if (doRefresh) {
            this.refresh().then(() => {
                if (to_load) {
                    // Check if the hash of to_load matches one of our options, and if so, select it
                    let found = false;
                    for (let i = 0; i < this.selectElement.options.length; i++) {
                        const option = this.selectElement.options[i];
                        if (option.value === to_load["hash"]) {
                            option.selected = true;
                            this.value = to_load["hash"];
                            found = true;
                        } else {
                            option.selected = false;
                        }
                    }
                    if (!found) {
                        this.selectElement.options[0].selected = true;
                        this.value = "none";
                    }
                }
            });
        }
    }

    async refresh() {
        // Display "Loading..." in the select element
        this.selectElement.innerHTML = '<option value="" selected>Loading...</option>';

        let modelList = await sendMessage("models", {
            model_type: this.model_type,
            ext_include: this.ext_include,
            ext_exclude: this.ext_exclude
        });
        console.log("Model list: ", modelList);
        this.modelList = modelList;
        this.selectElement.innerHTML = "";
        const loaded = modelList["loaded"];
        this.value = (loaded === undefined || loaded === null ? "none" : loaded);
        let blankOption = document.createElement("option");
        blankOption.value = "none";

        if (this.value === "none") {
            blankOption.selected = true;
        }
        this.selectElement.appendChild(blankOption);

        if (modelList.models) {
            modelList.models.forEach(model => {
                let option = document.createElement("option");
                option.value = (model.hasOwnProperty("hash") ? model.hash : "none");
                if (this.value !== "none" && this.value !== undefined) {
                    if (this.value === option.value) {
                        option.selected = true;
                    }
                }
                option.textContent = model.display_name;
                this.selectElement.appendChild(option);
            });
        }
    }


    getModel() {
        if (this.multiple) {
            // If this.value is an array, enumerate
            if (Array.isArray(this.value)) {
                let models = [];
                for (let i = 0; i < this.value.length; i++) {
                    const hash = this.value[i];
                    let model = this.modelList.models.find(
                        model => model.hash === hash
                    );
                    if (model) {
                        models.push(model);
                    }
                }
                return models;
            }
        } else {
            if (this.value === "none" || this.value === undefined) {
                return null;
            }
            return this.modelList.models.find(
                model => model.hash === this.value
            );
        }
    }

    val() {
        return this.getModel();
    }

    getValue() {
        return this.val();
    }

    setValue(value) {
        let isValid = false;
        for (let i = 0; i < this.selectElement.options.length; i++) {
            const option = this.selectElement.options[i];
            option.selected = option.value === value;
            isValid = true;
            break;
        }
        if (isValid) {
            this.value = value;
        }
    }

    setOnClickHandler(callback) {
        this.selectElement.onclick = () => {
            let selectedOption = this.selectElement.options[
                this.selectElement.selectedIndex
                ];
            if (selectedOption.value !== "none") {
                let selectedModel = this.modelList.models.find(
                    model => model.hash === selectedOption.value
                );
                callback(selectedModel);
            }
        };
    }

    setOnChangeHandler(callback) {
        this.onchangeCallbacks.push(callback);
    }
}

$.fn.modelSelect = function (inputOptions) {
    this.each(function () {
        const $this = $(this);
        let select = $this.data("ModelSelect");

        if (!select) {
            const targetElement = this;
            const targetDataset = targetElement.dataset;
            const defaultOptions = {
                model_type: "diffusers",
                ext_include: [],
                ext_exclude: [],
                load_on_select: false,
                value: "none",
                label: "",
                key: $(this).id,
                multiple: false,
                addClass: ""
            };

            const options = {
                ...defaultOptions,
                ...targetDataset,
                ...inputOptions
            };

            select = new ModelSelect(targetElement, options);
            $this.data("ModelSelect", select);
        }
    });

    return this.data("ModelSelect");
};



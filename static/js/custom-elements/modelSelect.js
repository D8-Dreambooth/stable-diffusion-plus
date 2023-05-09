class ModelSelect {

    static modelSelectMap = new Map();

    constructor(container, options) {
        const existingInstance = ModelSelect.modelSelectMap.get(container);
        if (existingInstance) {
            return existingInstance;
        }
        registerSocketMethod(container, "reload_models", this.modelSocketUpdate.bind(this));
        this.container = container;
        this.model_type = options.model_type || "stable-diffusion";
        this.ext_include = options.ext_include || [".safetensors"];
        this.ext_exclude = options.ext_exclude || [];
        console.log("Model select options:", options);
        this.multiple = options.multiple || false;
        this.load_on_select = options.load_on_select || false;
        this.modelList = [];
        this.selectElement = document.createElement("select");
        this.selectElement.classList.add("form-control");
        this.selectElement.classList.add("model-select");
        if (this.multiple) {
            this.selectElement.setAttribute("multiple", "true");
        }
        this.selectElement.dataset["ModelSelect"] = this;
        this.selectElement.dataset["key"] = options.key || container.id;
        const addClass = options.addClass || "";
        if (addClass !== "") {
            this.selectElement.classList.add(addClass);
        }
        this.selectElement.id = container.id + "_select";
        this.currentModel = options.value || "none";
        const wrapper = document.createElement("div");
        wrapper.classList.add("form-group");

        if (options.label) {
            const labelElement = document.createElement("label");
            labelElement.setAttribute("for", this.selectElement.id);
            labelElement.textContent = options.label;
            labelElement.classList.add("form-label");
            wrapper.appendChild(labelElement);
        }

        wrapper.appendChild(this.selectElement);
        this.container.appendChild(wrapper);
        this.setOnChangeHandler((selectedModel) => {
            console.log("Selected model (chang):", selectedModel);
            if (this.multiple) {
                this.currentModel = selectedModel;
            } else if (selectedModel.hasOwnProperty("hash")) {
                this.currentModel = selectedModel.hash;
            }
        });
        this.refresh();
        ModelSelect.modelSelectMap.set(container, this);
        return this;
    }

    modelSocketUpdate(data) {
        console.log("Model socket update:", data);
        const modelType = data.model_type;
        const to_load = data["to_load"];
        let modelTypes = [modelType];
        if (this.model_type.indexOf("_") !== -1) {
            modelTypes = this.model_type.split("_");
        }
        let doRefresh = false;
        for (let i = 0; i < modelTypes.length; i++) {
            if (modelTypes[i] === modelType) {
                doRefresh = true;
                break;
            }
        }
        if (doRefresh) {
            this.refresh().then(() => {
                console.log("Refreshed model list");
                if (to_load) {
                    console.log("Selecting model:", to_load);
                    // Check if the hash of to_load matches one of our options, and if so, select it
                    let found = false;
                    for (let i = 0; i < this.selectElement.options.length; i++) {
                        const option = this.selectElement.options[i];
                        if (option.value === to_load["hash"]) {
                            option.selected = true;
                            found = true;
                        } else {
                            option.selected = false;
                        }
                    }
                    if (!found) {
                        this.selectElement.options[0].selected = true;
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

        this.modelList = modelList;
        this.selectElement.innerHTML = "";
        let blankOption = document.createElement("option");
        blankOption.value = "none";
        console.log("Got model list: ", modelList);
        const loaded = modelList["loaded"];
        this.currentModel = (loaded === undefined || loaded === null ? "none" : loaded);

        if (this.currentModel === "none") {
            blankOption.selected = true;
        }

        this.selectElement.appendChild(blankOption);

        if (modelList.models) {
            modelList.models.forEach(model => {
                let option = document.createElement("option");
                option.value = (model.hasOwnProperty("hash") ? model.hash : "none");
                if (this.currentModel !== "none" && this.currentModel !== undefined) {
                    if (this.currentModel === option.value) {
                        option.selected = true;
                    }
                }
                option.textContent = model.display_name;
                this.selectElement.appendChild(option);
            });
        }
    }


    getModel() {
        if (this.multiple) return this.currentModel;
        const selectedOption = this.selectElement.options[this.selectElement.selectedIndex];

        if (selectedOption.value === "none") {
            return undefined;
        }

        const selectedHash = selectedOption.value;

        const selectedModel = this.modelList.models.find(
            model => model.hash === selectedHash
        );

        if (!selectedModel) {
            console.log("Model not found with hash:", selectedHash);
            return undefined;
        }

        return selectedModel;
    }

    val() {
        return this.getModel();
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
        this.selectElement.onchange = () => {
            // Get the selected options from the select element
            const selectedOptions = Array.from(this.selectElement.options)
                .filter(option => option.selected && option.value !== "none");
            if (selectedOptions.length > 0) {
                let selectedModels = selectedOptions.map(selectedOption => {
                    // Find the model that matches the selected option value
                    return this.modelList.models.find(
                        model => model.hash === selectedOption.value
                    );
                });
                if (this.load_on_select && !this.multiple) {
                    // Add the model type to each selected model
                    selectedModels.forEach(selectedModel => {
                        selectedModel["model_type"] = this.model_type;
                        sendMessage("load_model", selectedModel);
                    });
                }

                if (!this.multiple && selectedModels.length > 0) {
                    selectedModels = selectedModels[0];
                }
                callback(selectedModels);


            } else {
                this.currentModel = "none";
            }
        };
    }


    static init(selector, options = {}) {
        const elements = new Map();
        $(selector).each((index, element) => {
            if (elements.has(element)) {
                return elements.get(element);
            }
            const data = $(element).data();
            const optionsWithDefault = {
                model_type: (data && data.model_type) || (options && options.model_type) || "stable-diffusion",
                ext_include: (data && (typeof data.ext_include === "string" ? [data.ext_include] : data.ext_include)) || (options && (typeof options.ext_include === "string" ? [options.ext_include] : options.ext_include)) || [],
                ext_exclude: (data && (typeof data.ext_exclude === "string" ? [data.ext_exclude] : data.ext_exclude)) || (options && (typeof options.ext_exclude === "string" ? [options.ext_exclude] : options.ext_exclude)) || [],
                load_on_select: (data && data.load_on_select) || (options && options.load_on_select) || false,
                value: (data && data.value) || (options && options.value) || "none",
                label: (data && data.label) || (options && options.label) || "",
                key: (data && data.key) || (options && options.key) || $(element.id),
                multiple: (data && data.multiple) || (options && options.multiple) || false,
                addClass: (data && data.add_class) || (options && options.addClass) || ""
            };

            if (typeof optionsWithDefault.ext_include === "string") {
                optionsWithDefault.ext_include = [optionsWithDefault.ext_include];
            }
            if (typeof optionsWithDefault.ext_exclude === "string") {
                optionsWithDefault.ext_exclude = [optionsWithDefault.ext_exclude];
            }


            const modelSelect = new ModelSelect(element, optionsWithDefault);
            elements.set(element, modelSelect);
        });
        return Array.from(elements.values());
    }


}

$.fn.modelSelect = function (options) {
    return ModelSelect.init(this, options);
};



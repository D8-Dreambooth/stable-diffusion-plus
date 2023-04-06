class ModelSelect {

    static modelSelectMap = new Map();

    constructor(container, options) {
        const existingInstance = ModelSelect.modelSelectMap.get(container);
        if (existingInstance) {
            return existingInstance;
        }
        registerSocketMethod(container, "reload_models", this.modelSocketUpdate);
        this.container = container;
        this.model_type = options.model_type || "stable-diffusion";
        this.ext_include = options.ext_include || [".safetensors"];
        this.ext_exclude = options.ext_exclude || [];
        this.load_on_select = options.load_on_select || false;
        this.modelList = [];
        this.selectElement = document.createElement("select");
        this.selectElement.classList.add("form-control");
        this.selectElement.classList.add("model-select");
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
            this.currentModel = selectedModel;
        });
        this.refresh();
        ModelSelect.modelSelectMap.set(container, this);
        return this;
    }

    modelSocketUpdate(data) {
        console.log("Model socket update:", data);
    }

    async refresh() {
        let modelList = await sendMessage("models", {
            model_type: this.model_type,
            ext_include: this.ext_include,
            ext_exclude: this.ext_exclude
        });
        console.log("Model list: ", modelList);
        this.modelList = modelList;
        this.selectElement.innerHTML = "";
        let blankOption = document.createElement("option");
        blankOption.value = "none";
        const loaded = modelList["loaded"];
        if (loaded !== undefined && loaded !== null) {
            console.log("Loaded: ", loaded);
            this.currentModel = loaded.hash;
        }

        if (this.currentModel === "none") {
            blankOption.selected = true;
        }

        this.selectElement.appendChild(blankOption);
        if (modelList.models) {
            modelList.models.forEach(model => {
                let option = document.createElement("option");
                option.value = (model.hasOwnProperty("hash") ? model.hash : "none");
                if (this.currentModel.hash === option.value) {
                    option.selected = true;
                }
                option.textContent = model.display_name;
                this.selectElement.appendChild(option);
            });
        }
    }

    getModel() {
        const selectedOption = this.selectElement.options[this.selectElement.selectedIndex];

        if (selectedOption.value === "none") {
            console.log("No model selected");
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

        console.log("Selected model: ", selectedModel);
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
            let selectedOption = this.selectElement.options[
                this.selectElement.selectedIndex
                ];
            if (selectedOption.value !== "none") {
                let selectedModel = this.modelList.models.find(
                    model => model.hash === selectedOption.value
                );
                if (this.load_on_select) {
                    selectedModel["model_type"] = this.model_type;
                    let result = sendMessage("load_model", selectedModel);
                }
                callback(selectedModel);
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
                model_type: data.model_type || options.model_type || "stable-diffusion",
                ext_include: data.ext_include || options.ext_include || [".safetensors"],
                ext_exclude: data.ext_exclude || options.ext_exclude || [],
                load_on_select: data.load_on_select || options.load_on_select || false,
                value: data.value || options.value || "none",
                label: data.label || options.label || "",
                key: data.key || options.key || $(element.id),
                addClass: data.add_class || options.addClass || ""
            };
            const modelSelect = new ModelSelect(element, optionsWithDefault);
            elements.set(element, modelSelect);
        });
        return Array.from(elements.values());
    }


}

$.fn.modelSelect = function (options) {
    return ModelSelect.init(this, options);
};



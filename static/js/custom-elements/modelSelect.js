class ModelSelect {
    constructor(container, options) {
        this.container = container;
        this.model_type = options.model_type || "stable-diffusion";
        this.ext_include = options.ext_include || [".safetensors"];
        this.ext_exclude = options.ext_exclude || [];
        this.load_on_select = options.load_on_select || false;
        this.modelList = [];
        this.selectElement = document.createElement("select");
        this.selectElement.classList.add("form-control");
        this.selectElement.id = "inferModelSelection";
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
            console.log("Current model: ", selectedModel);
            this.currentModel = selectedModel;
        });
        this.addOptions();
    }

    async addOptions() {
        let modelList = await sendMessage("models", {
            model_type: this.model_type,
            ext_include: this.ext_include,
            ext_exclude: this.ext_exclude
        });
        this.modelList = modelList;
        console.log("Models: ", modelList);
        this.selectElement.innerHTML = "";
        let blankOption = document.createElement("option");
        blankOption.value = "none";
        const loaded = modelList["loaded"];
        console.log("Loaded: ", loaded);
        if (loaded !== undefined) {
            this.selectedModel = loaded;
        }

        if (this.selectedModel === "none") {
            blankOption.selected = true;
        }

        this.selectElement.appendChild(blankOption);
        modelList.models.forEach(model => {
            let option = document.createElement("option");
            option.value = model.hash;
            if (this.selectedModel === option.value) {
                option.selected = true;
            }
            option.textContent = model.display_name;
            this.selectElement.appendChild(option);
        });
    }

    getModel() {
        const selectedOption = this.selectElement.options[this.selectElement.selectedIndex];
        console.log("Selected option:", selectedOption);

        if (selectedOption.value === "none") {
            console.log("No model selected");
            return undefined;
        }

        const selectedHash = selectedOption.value;
        console.log("Looking for model with hash:", selectedHash);

        const selectedModel = this.modelList.models.find(
            model => model.hash === selectedHash
        );

        if (!selectedModel) {
            console.log("Model not found with hash:", selectedHash);
            return undefined;
        }

        console.log("Selected model:", selectedModel);
        return selectedModel;
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
            console.log("Change handler: ", selectedOption);
            if (selectedOption.value !== "none") {
                let selectedModel = this.modelList.models.find(
                    model => model.hash === selectedOption.value
                );
                console.log("Setting selected model: ", selectedModel);
                if (this.load_on_select) {
                    selectedModel["model_type"] = this.model_type;
                    console.log("Loading model:", selectedModel);
                    let result = sendMessage("load_model", selectedModel);
                }
                callback(selectedModel);
            } else {
                console.log("No model...");
                this.currentModel = "none";
            }
        };
    }

    selectedModel() {
        return this.currentModel;
    }
}

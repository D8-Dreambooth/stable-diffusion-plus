class ModelSelect {
    constructor(container, options) {
        this.container = container;
        this.model_type = options.model_type || "stable-diffusion";
        this.ext_include = options.ext_include || [".safetensors"];
        this.ext_exclude = options.ext_exclude || [];
        this.modelList = [];
        this.selectElement = document.createElement("select");
        this.selectElement.classList.add("form-control");
        this.selectElement.id = "inferModelSelection";
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
        this.selectElement.appendChild(blankOption);
        modelList.models.forEach(model => {
            let option = document.createElement("option");
            option.value = model.hash;
            option.textContent = model.display_name;
            this.selectElement.appendChild(option);
        });
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
                callback(selectedModel);
            }
        };
    }
}

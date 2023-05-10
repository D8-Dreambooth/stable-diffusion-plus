class Module {
    constructor(name, id, icon, is_default, index, init_method = null, reload_method = null) {
        this.name = name;
        this.id = id;
        this.icon = icon;
        this.is_default = is_default;
        this.index = index;
        this.init_method = init_method;
        this.reload_method = reload_method;
        this.systemConfig = null;
        this.moduleDefaults = null;
        this.moduleLink = null;
        registerModule(this);
    }

    async init(systemConfig, moduleDefaults, locales) {
        this.systemConfig = systemConfig;
        this.moduleDefaults = moduleDefaults;
        console.log("Defaults: ", this.moduleDefaults);
        let module_id = this.id;
        let module_name = this.name;
        let module_icon = this.icon;
        let is_default = this.is_default;
        let index = this.index;
        let navList = document.getElementById("navList");
        let existingModule = document.getElementById(module_id + "_link");
        let newModule;

        if (existingModule) {
            navList.removeChild(existingModule);
        }

        newModule = document.createElement("a");
        newModule.href = "#";
        newModule.className = "nav_link";
        newModule.id = module_id + "_link";
        moduleIds[module_id] = module_name;
        newModule.setAttribute("data-index", index); // Add data-index attribute

        let icon = document.createElement("i");
        icon.className = `bx bx-${module_icon} nav_icon`;

        let name = document.createElement("span");
        name.className = "nav_name";
        name.textContent = module_name;

        newModule.appendChild(icon);
        newModule.appendChild(name);
        navList.appendChild(newModule);
        this.moduleLink = newModule;
        newModule.addEventListener("click", function () {
            showPane(module_id);
        });

        if (is_default) {
            showPane(module_id);
        }

        // Sort navList by data-index
        let navLinks = Array.from(navList.children);
        navLinks.sort((a, b) => {
            let aIndex = parseInt(a.getAttribute("data-index"));
            let bIndex = parseInt(b.getAttribute("data-index"));
            if (aIndex === -1) {
                if (bIndex === -1) {
                    return a.textContent.localeCompare(b.textContent); // Sort alphabetically if both have index of -1
                } else {
                    return 1; // Append "a" to the end
                }
            } else if (bIndex === -1) {
                return -1; // Append "b" to the end
            } else {
                return aIndex - bIndex;
            }
        });

        // Re-add sorted navLinks to navList
        navList.innerHTML = "";
        for (let link of navLinks) {
            navList.appendChild(link);
        }
        if (this.init_method !== null) {
            this.init_method();
        }
        this.populateInputs(this.moduleDefaults);
        this.localize(locales);
    }

    localize(module_locales) {
        const container = document.getElementById(this.id);
        const elements = container.querySelectorAll("*");
        let mapped = {};
        if (module_locales["module"]) {
            let {label, title} = module_locales["module"];
            if (label) {
                this.moduleLink.querySelector(".nav_name").innerHTML = label;
            }
            if (title) {
                this.moduleLink.setAttribute("title", title);
            }
        }
        elements.forEach((element) => {
            let elem_id = null;
            if (element.hasAttribute("for")) {
                elem_id = element.getAttribute("for");
            }
            if (elem_id === null) return;
            let d = "";
            let t = "";
            let l = "";
            let ls = element.innerHTML.split("\n");
            let lt = [];
            for (let i = 0; i < ls.length; i++) {
                let line = ls[i];
                if (line.trim() !== "") {
                    lt.push(line.trim());
                    break;
                }
            }
            l = lt.join(" ");
            l = l.trim();
            if (module_locales[elem_id]) {
                let {label, title, description} = module_locales[elem_id];
                if (title) {
                    t = title;
                    element.setAttribute("title", title);
                }
                if (description) {
                    d = description;
                    element.setAttribute("data-description", description);
                }
                if (label) {
                    l = label;
                    element.innerHTML = label;
                }
            }
            if (l !== "" && l.indexOf("<") === -1) {
                mapped[elem_id] = {
                    label: l,
                    title: t,
                    description: d
                };
            }
        });
        localData[this.id] = mapped;
    }

    async reload() {
        if (this.reload_method !== null) {
            await this.reload_method;
        }
    }

    async unload() {
        deregisterModule(this.id);
        let navList = document.getElementById("navList");
        let existingModule = document.getElementById(this.id + "_link");
        if (existingModule) {
            navList.removeChild(existingModule);
        }
    }

    enumerateInputs() {
        const element = document.getElementById(this.id);
        const inputDict = {};
        const inputElements = element.querySelectorAll('input, select');

        for (let i = 0; i < inputElements.length; i++) {
            const input = inputElements[i];
            const inputId = input.id;

            if (input.type === 'checkbox') {
                inputDict[inputId] = {
                    value: input.checked
                };
            } else if (input.type === 'range') {
                inputDict[inputId] = {
                    value: parseFloat(input.value),
                    min: parseFloat(input.min),
                    max: parseFloat(input.max),
                    step: parseFloat(input.step)
                };
            } else if (input.tagName.toLowerCase() === 'select') {
                const options = input.querySelectorAll('option');
                const optionDict = {};

                for (let j = 0; j < options.length; j++) {
                    const option = options[j];
                    if (option.text !== "Loading...") {
                        optionDict[option.value] = option.text;
                    }
                }

                inputDict[inputId] = {
                    value: input.value,
                    options: optionDict
                };
            } else {
                inputDict[inputId] = {
                    value: parseFloat(input.value) || input.value
                };
            }
        }

        return inputDict;
    }

    populateInputs(inputDict) {
        const element = document.getElementById(this.id);

        for (const inputId in inputDict) {
            if (inputId === "") continue;
            console.log("Populating input " + inputId + " in module " + this.id + ".");
            let inputElements;
            try {
                inputElements = element.querySelectorAll('#' + inputId);
            } catch (e) {
                console.log(e);
            }
            if (!inputElements) continue;
            if (!inputElements.length) continue;
            const inputData = inputDict[inputId];
            for (let i = 0; i < inputElements.length; i++) {
                const inputElement = inputElements[i];

                if (inputElement.type === 'checkbox') {
                    inputElement.checked = inputData.value;
                } else if (inputElement.type === 'range') {
                    inputElement.value = inputData.value;
                    inputElement.min = inputData.min;
                    inputElement.max = inputData.max;
                    inputElement.step = inputData.step;
                } else if (inputElement.tagName.toLowerCase() === 'select') {
                    while (inputElement.firstChild) {
                        inputElement.removeChild(inputElement.firstChild);
                    }

                    for (const value in inputData.options) {
                        const option = document.createElement('option');
                        option.value = value;
                        option.text = inputData.options[value];
                        inputElement.add(option);
                    }
                    // Select the item from the input options if it exists
                    let options = inputElement.querySelectorAll('option');
                    for (let j = 0; j < options.length; j++) {
                        const option = options[j];
                        if (option.value === inputData.value) {
                            option.selected = true;
                            break;
                        }
                    }
                    inputElement.value = inputData.value;
                } else {
                    console.log("Setting input " + inputId + " to " + inputData.value + ".");
                    inputElement.value = inputData.value;
                }
            }
        }
    }


}
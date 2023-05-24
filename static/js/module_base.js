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
        this.moduleLink = null
        console.log("Registering: ", this);
        registerModule(this);
    }

    async init(systemConfig, moduleDefaults, locales) {
        this.systemConfig = systemConfig;
        this.moduleDefaults = moduleDefaults;
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

        this.localize(locales);
        setTimeout(() => {
            this.populateInputs(this.moduleDefaults);
        }, 1000);
    }

    localize(module_locales) {
        const container = document.getElementById(this.id);
        const elements = container.querySelectorAll("*");
        let mapped = {};
        if (module_locales["module"]) {
            let {label, title} = module_locales["module"];
            if (label) {
                this.moduleLink.querySelector(".nav_name").innerHTML = label;
                moduleIds[this.id] = label;
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
            let l;
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
            console.log("Reloading " + this.id);
            this.reload_method();
        }
        //this.localize(locales);
        setTimeout(() => {
            this.populateInputs(this.moduleDefaults);
        }, 1000);
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
                if (inputElement.classList.contains("bootstrapSlider")) {
                    let bs = $(inputElement).BootstrapSlider();
                    bs.setValue(inputData.value);
                    if (inputData.hasOwnProperty("min")) bs.setMin(inputData.min);
                    if (inputData.hasOwnProperty("max")) bs.setMax(inputData.max);
                    if (inputData.hasOwnProperty("step")) bs.setStep(inputData.step);

                } else if (inputElement.classList.contains("nav-tabs")) {
                    console.log("nav-tabs");
                    let navLinks = inputElement.querySelectorAll(".nav-link");

                    // Loop through each nav link
                    navLinks.forEach((link) => {
                        // Remove the "active" class from all nav links
                        link.classList.remove("active");

                        // Untoggle the associated tab content
                        let target = document.querySelector(link.getAttribute("data-bs-target"));
                        if (target) {
                            target.classList.remove("show");
                            target.classList.remove("active");
                        }
                    });

                    // Set the target link as active
                    let targetLink = document.getElementById(inputData.value);
                    if (targetLink) {
                        targetLink.classList.add("active");

                        // Toggle the associated tab content
                        let targetTab = document.querySelector(targetLink.getAttribute("data-bs-target"));
                        if (targetTab) {
                            targetTab.classList.add("show");
                            targetTab.classList.add("active");
                        }
                    }

                } else if (inputElement.type === 'checkbox') {
                    inputElement.checked = inputData.value;

                } else if (inputElement.tagName.toLowerCase() === 'select') {
                    const values = new Set(Array.from(inputElement.options).map(option => option.value));
                    for (const value in inputData.options) {
                        if (!values.has(value)) {
                            const option = document.createElement('option');
                            option.value = value;
                            option.text = inputData.options[value];
                            inputElement.add(option);
                        }
                    }
                    // Select the item from th  e input options if it exists
                    const selectedOption = inputElement.querySelector(`option[value="${inputData.value}"]`);
                    if (selectedOption) {
                        selectedOption.selected = true;
                    }
                    if (inputId.indexOf("_select") !== -1) {
                        let msId = inputId.replace("_select", "");
                        let ms = $("#" + msId).modelSelect();
                        if (ms) {
                            ms.setValue(inputData.value);
                        }
                    }
                } else {
                    inputElement.value = inputData.value;
                }
            }
        }
    }

    getSettings(inputSelector, ignore) {
        let container = $("#" + this.id);
        // Select inputs with selector in container
        let inputs = container.find(inputSelector);
        let settings = {};
        inputs.each((index, element) => {
            let id = element.id;
            let doIgnore = false;
            // If ignore is an array of strings
            if (Array.isArray(ignore)) {
                // Loop through each string
                ignore.forEach((ignoreId) => {
                    // If the element id contains the string, skip it
                    if (ignoreId !== "" && id.indexOf(ignoreId) !== -1) {
                        doIgnore = true;
                    }
                });
            } else {
                if (ignore !== "" && id.indexOf(ignore) !== -1) {
                    doIgnore = true;
                }
            }

            if (doIgnore) return;

            if (id === null || id === "" || id === "undefined") {
                console.log("invalid element: ", element);
                return;
            }

            let value;
            let elem_selector = "#" + id;
            let tryParse = false;
            if ($(element).hasClass("db-file-browser")) {
                value = element.dataset.value;
            } else if ($(element).hasClass("db-slider")) {
                tryParse = true;
                value = $(elem_selector).BootstrapSlider().getValue();
            } else if ($(element).is(":checkbox")) {
                value = $(element).is(":checked");
            } else if ($(element).is(":radio")) {
                if ($(element).is(":checked")) {
                    value = $(element).val();
                }
            } else if ($(element).is("select")) {
                value = $(element).val();
            } else if ($(element).is("input[type='number']")) {
                tryParse = true;
                value = $(element).val();
            } else {
                value = $(element).val();
            }

            if (typeof value === "undefined") {
                value = "";
            }

            if (tryParse) {
                if (!isNaN(parseFloat(value))) {
                    value = parseFloat(value);
                } else if (!isNaN(parseInt(value))) {
                    value = parseInt(value);
                }
            }

            settings[id] = value;
        });
        return settings;
    }

}
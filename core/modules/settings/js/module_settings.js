const settingsModule = new Module("Settings", "moduleSettings", "cog", false, 1000, initSettings);
let userFormCreated = false;
let currentUser;
function initSettings() {
    let protectedData = this.systemConfig;
    let modules = this.moduleDefaults;
    let locales = this.localeData;
    console.log("Initializing settings module", protectedData, modules, locales);
    // Register the module with the UI. Icon is from boxicons by default.
    let adminUser = false;
    if (this.currentUser !== undefined) {
        adminUser = this.currentUser["admin"];
    }
    loadSettings(protectedData, adminUser);
}

function loadSettings(settingData, adminUser) {
    console.log("Retrieved settings, loading (2)", settingData, currentUser);
    const systemSection = settingData["core"];
    const usersSection = settingData["users"];


    let tabs = [];

    let usersForm;
    if (usersSection !== undefined && usersSection[0] !== null) {
        usersForm = createUserForm(usersSection);
    }

    if (usersForm !== undefined) {
        tabs.push({name: 'Users', content: usersForm});
    }

    if (adminUser) {
        const otherSections = Object.entries(settingData).filter(
            ([key]) => key !== 'core' && key !== "users"
        );

        const systemForm = createForm(systemSection, 'System');
        tabs.push({name: 'System', content: systemForm});

        const otherForms = otherSections.map(([key, value]) => {
            const titleCaseKey = key.replace(/_/g, ' ').toTitleCase();
            const form = createForm(value, titleCaseKey);
            return {name: titleCaseKey, content: form};
        });


        tabs = tabs.concat(otherForms);
    }
    const tabContainer = document.getElementById('appSettingsContainer');
    tabContainer.innerHTML = '';
    createTabs(tabs, tabContainer);
}


function createForm(section, sectionName) {
    const form = document.createElement('form');
    form.setAttribute('data-section', sectionName);
    Object.entries(section).forEach(([key, value]) => {
        const label = key.replace(/_/g, ' ').toTitleCase();
        let input;

        if (typeof value === 'boolean') {
            input = createCheckbox(value, label, `${sectionName}_${key}`);
        } else if (typeof value === 'number') {
            input = createInput(value, label, `${sectionName}_${key}`, 'number');
        } else {
            input = createInput(value, label, `${sectionName}_${key}`);
        }
        input.classList.add("form-control");
        const inputWrapper = document.createElement('div');
        inputWrapper.setAttribute('class', 'form-group');
        inputWrapper.appendChild(input);

        const fieldset = document.createElement('fieldset');
        fieldset.appendChild(inputWrapper);

        form.appendChild(fieldset);
    });

    return form;
}


function createTabs(sections, parent) {
    const tabsContainer = document.createElement('div');
    tabsContainer.setAttribute('class', 'tab-container');

    const tabsList = document.createElement('ul');
    tabsList.setAttribute('class', 'nav nav-tabs');
    let firstSection = true;
    sections.forEach(({name, content}) => {
        const tabListItem = document.createElement('li');
        tabListItem.setAttribute('class', 'nav-item');
        const tabLink = document.createElement('a');
        tabLink.setAttribute('href', `#${name}-settings`);
        tabLink.setAttribute('class', 'nav-link');
        tabLink.innerText = name;
        tabLink.addEventListener('click', (event) => {
            event.preventDefault();
            const tabPanes = document.getElementsByClassName('tab-pane');
            for (let i = 0; i < tabPanes.length; i++) {
                tabPanes[i].classList.remove('active');
            }
            const tabs = document.getElementsByClassName('nav-link');
            for (let i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            event.target.classList.add('active');
            document.getElementById(name + "-settings").classList.add('active');
        });

        const tabContent = document.createElement('div');
        tabContent.setAttribute('id', name + "-settings");
        tabContent.setAttribute('class', 'tab-pane');
        if (firstSection) {
            tabLink.classList.add("active");
            tabContent.classList.add("active");
            firstSection = false;
        }

        const formContainer = document.createElement('div');
        formContainer.setAttribute('class', 'form-container');
        formContainer.appendChild(content);
        tabContent.appendChild(formContainer);

        tabListItem.appendChild(tabLink);
        tabsList.appendChild(tabListItem);
        tabsContainer.appendChild(tabContent);
    });

    tabsList.firstChild.setAttribute('class', 'nav-item active');
    tabsContainer.insertBefore(tabsList, tabsContainer.firstChild);

    parent.appendChild(tabsContainer);
    let timeoutId = null;

    $(".sysInput").change(function () {
        let sectionName = $(this).attr("name").split("_")[0].toLowerCase();
        if (sectionName === "system") {
            sectionName = "core";
        }

        let paramName = $(this).attr('name');
        const underscoreIndex = paramName.indexOf('_');
        paramName = paramName.substr(underscoreIndex + 1);
        const paramValue = $(this).is(':checkbox') ? $(this).prop('checked') : $(this).val();
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
        }
        let endpoint = "set_settings";
        let data = {};
        if ($(this).attr("data-section") === "users") {
            endpoint = "update_user";

            data = {"name": sectionName};
            data[paramName] = paramValue;
        } else {
            data = {"section": sectionName, "key": paramName, "value": paramValue};
        }
        timeoutId = setTimeout(() => {
            sendMessage(endpoint, data).then((res) => {
                timeoutId = null;
            if (res.name === "update_user") return;
            if (sectionName !== "core" && sectionName !== "users") {
                console.log("Refreshing section: " + sectionName, modules);
                for (let i = 0; i < modules.length; i++) {
                    console.log(modules[i].id.toLowerCase(), "module" + sectionName);
                    if (modules[i].id.toLowerCase() === "module" + sectionName) {
                        modules[i].systemConfig[paramName] = paramValue;
                        console.log("Refreshing: ", modules[i]);
                        modules[i].reload();
                        break;
                    }
                }
            }
            });
        }, 500);
    });
}


String.prototype.toTitleCase = function () {
    return this.replace(/\w\S*/g, function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
};


function createUserForm(users) {
    userFormCreated = true;
    console.log("Creating user form: ", users);
    const form = document.createElement("form");
    form.setAttribute("data-section", "users");
    form.setAttribute("class", "row g-2");

    Object.entries(users).forEach(([key, user]) => {
        console.log("Creating user: ", user);
        const userDiv = document.createElement("div");
        userDiv.setAttribute("class", "user-div col-12");
        const username = user.name;
        const passwordDiv = document.createElement("div");
        passwordDiv.setAttribute("class", "password-div col-12");
        passwordDiv.style.display = "none";

        const passwordInput = createInput(
            "",
            `Password:`,
            "password",
            "form-control"
        );

        const confirmPasswordInput = createInput(
            "",
            `Confirm Password:`,
            "confirmPassword",
            "form-control"
        );

        [...passwordInput.children].forEach(child => child.classList.remove("sysInput"));
        [...confirmPasswordInput.children].forEach(child => child.classList.remove("sysInput"));

        const changePasswordButton = document.createElement("button");
        changePasswordButton.innerText = "Change password";
        changePasswordButton.setAttribute("class", "btn btn-primary mb-2");
        changePasswordButton.addEventListener("click", (event) => {
            event.preventDefault();
            passwordDiv.style.display = "block";
        });

        const updateButton = document.createElement("button");
        updateButton.disabled = true;
        updateButton.innerText = "Update";
        updateButton.setAttribute("class", "btn btn-primary");
        updateButton.addEventListener("click", (event) => {
            event.preventDefault();
            const password = passwordInput.querySelector("input").value;
            sendMessage("change_password", {"user": username, "password": password}).then((res) => {
                if (res.status === "Password updated successfully.") {
                    cancelButton.click();
                }
            });
        });

        // Delay in milliseconds before checking for password match
        const delay = 100;

        let timeoutId = null;

        passwordInput.querySelector("input").addEventListener("input", () => {
            // Clear any existing timeout
            clearTimeout(timeoutId);

            // Set a new timeout to check for password match after delay
            timeoutId = setTimeout(() => {
                const password = passwordInput.querySelector("input").value;
                const confirmPassword = confirmPasswordInput.querySelector("input").value;

                if (password === confirmPassword && password !== "" && confirmPassword !== "") {
                    // Passwords match
                    confirmPasswordInput.style.borderColor = "";
                    updateButton.disabled = false;
                } else {
                    // Passwords do not match or are blank
                    confirmPasswordInput.style.borderColor = "red";
                    updateButton.disabled = true;
                }
            }, delay);
        });

        confirmPasswordInput.querySelector("input").addEventListener("input", () => {
            // Clear any existing timeout
            clearTimeout(timeoutId);

            // Set a new timeout to check for password match after delay
            timeoutId = setTimeout(() => {
                const password = passwordInput.querySelector("input").value;
                const confirmPassword = confirmPasswordInput.querySelector("input").value;

                if (password === confirmPassword && password !== "" && confirmPassword !== "") {
                    // Passwords match
                    confirmPasswordInput.style.borderColor = "";
                    updateButton.disabled = false;
                } else {
                    // Passwords do not match or are blank
                    confirmPasswordInput.style.borderColor = "red";
                    updateButton.disabled = true;
                }
            }, delay);
        });


        const cancelButton = document.createElement("button");
        cancelButton.innerText = "Cancel";
        cancelButton.setAttribute("class", "btn btn-secondary mx-2");
        cancelButton.addEventListener("click", (event) => {
            event.preventDefault();
            passwordDiv.style.display = "none";
            passwordInput.value = "";
            confirmPasswordInput.value = "";
        });

        userDiv.appendChild(document.createElement("hr"));
        userDiv.appendChild(document.createElement("div"));
        userDiv.lastChild.setAttribute("class", "col-6 col-md-12");
        userDiv.lastChild.appendChild(document.createTextNode(`User: ${username.toTitleCase()}`));
        let adminCheckbox = "";
        if (user.hasOwnProperty("admin")) {
            adminCheckbox = createCheckbox(user.admin, "Admin User", user.name + "_admin", true);
            userDiv.lastChild.appendChild(adminCheckbox);
        }

        userDiv.appendChild(changePasswordButton);
        userDiv.appendChild(passwordDiv);
        passwordDiv.appendChild(passwordInput);
        passwordDiv.appendChild(confirmPasswordInput);
        passwordDiv.appendChild(updateButton);
        passwordDiv.appendChild(cancelButton);
        form.appendChild(userDiv);
    });

    return form;
}


function createCheckbox(value, label, name, user= false) {
    const formCheck = document.createElement('div');
    formCheck.setAttribute('class', 'form-check form-switch');

    const checkbox = document.createElement('input');
    checkbox.setAttribute('type', 'checkbox');
    checkbox.setAttribute('class', 'form-check-input sysInput');
    checkbox.setAttribute('data-section', user ? "users" : "core");
    checkbox.setAttribute('data-name', name.split('_')[1]);
    checkbox.setAttribute('name', name);
    checkbox.checked = value;

    const labelElem = document.createElement('label');
    labelElem.setAttribute('class', 'form-check-label');
    labelElem.setAttribute('for', name);
    labelElem.innerText = label;

    formCheck.appendChild(checkbox);
    formCheck.appendChild(labelElem);

    return formCheck;
}

function createInput(value, label, name, type = 'text') {
    const formGroup = document.createElement('div');
    formGroup.setAttribute('class', 'form-group');

    const labelElem = document.createElement('label');
    labelElem.setAttribute('for', name);
    labelElem.innerText = label;

    const input = document.createElement('input');
    input.setAttribute('type', type);
    input.setAttribute('value', value);
    input.setAttribute('name', name);
    input.setAttribute('class', 'form-control sysInput');
    input.setAttribute('data-section', 'system');
    input.setAttribute('data-name', name.split('_')[1]);

    formGroup.appendChild(labelElem);
    formGroup.appendChild(input);

    return formGroup;
}

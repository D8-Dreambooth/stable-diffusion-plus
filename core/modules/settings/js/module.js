document.addEventListener("DOMContentLoaded", function () {
    // Register the module with the UI. Icon is from boxicons by default.
    registerModule("Settings", "moduleSettings", "cog", false, 1000);
    sendMessage("get_settings", {}, true).then((res) => {
        console.log("Got settings res: ", res);
        parseObject(res);
    });
});

function parseObject(obj) {
    const systemSection = obj.shared.core;
    const usersSection = obj.protected.users;
    const otherSections = Object.entries(obj.shared).filter(
        ([key]) => key !== 'core'
    );
    console.log("SYS: ", systemSection);
    const systemForm = createForm(systemSection, 'System');
    console.log("US: ", usersSection);
    const usersForm = createUserForm(usersSection);
    console.log("OS: ", otherSections);
    const otherForms = otherSections.map(([key, value]) => {
        console.log("MAP: ", key, value);
        const titleCaseKey = key.replace(/_/g, ' ').toTitleCase();
        const form = createForm(value, titleCaseKey);
        return {name: titleCaseKey, content: form};
    });

    const tabs = [
        {name: 'System', content: systemForm},
        {name: 'Users', content: usersForm},
        ...otherForms
    ];

    const tabContainer = document.getElementById('appSettingsContainer');
    tabContainer.innerHTML = '';
    createTabs(tabs, tabContainer);
}

function createForm(section, sectionName) {
    const form = document.createElement('form');
    form.setAttribute('data-section', sectionName);
    console.log("PARSE: ", section);
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

        timeoutId = setTimeout(() => {
            console.log(`Section: ${sectionName}, Parameter Name: ${paramName}, Value: ${paramValue}`);
            sendMessage("set_settings", {"section": sectionName, "key": paramName, "value": paramValue}).then((res) => {
                console.log("Setting updated: ", res);
            });
            timeoutId = null;
        }, 500);
    });
}


String.prototype.toTitleCase = function () {
    return this.replace(/\w\S*/g, function (txt) {
        return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
    });
};


function createUserForm(users) {
    const form = document.createElement("form");
    form.setAttribute("data-section", "users");
    form.setAttribute("class", "row g-2");

    users.forEach((user) => {
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
            sendMessage("change_password", {"user": username, "password": password}).then((res)=>{
                console.log("Response: ", res);
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
                console.log("PW Change: ", password, confirmPassword);

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
                console.log("PW Change: ", password, confirmPassword);

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

        form.appendChild(document.createElement("hr"));
        form.appendChild(document.createElement("div"));
        form.lastChild.setAttribute("class", "col-12");
        form.lastChild.appendChild(document.createTextNode(`User: ${username.toTitleCase()}`));
        let adminCheckbox = "";
        if (user.hasOwnProperty("admin")) {
            adminCheckbox = createCheckbox(user.admin, "Admin User", "admin");
            form.lastChild.appendChild(adminCheckbox);
        }

        form.appendChild(changePasswordButton);
        form.appendChild(passwordDiv);
        passwordDiv.appendChild(passwordInput);
        passwordDiv.appendChild(confirmPasswordInput);
        passwordDiv.appendChild(updateButton);
        passwordDiv.appendChild(cancelButton);

    });

    return form;
}


function createCheckbox(value, label, name) {
    const formCheck = document.createElement('div');
    formCheck.setAttribute('class', 'form-check form-switch');

    const checkbox = document.createElement('input');
    checkbox.setAttribute('type', 'checkbox');
    checkbox.setAttribute('class', 'form-check-input sysInput');
    checkbox.setAttribute('data-section', 'system');
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

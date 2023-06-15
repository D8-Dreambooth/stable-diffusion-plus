let globalSocket = null;
let socketMethods = {};

const keyListener = new KeyListener();
const historyTracker = new HistoryTracker();
const imageReceivers = {};
const maskReceivers = {};
let messages = [];
// region Initialization

function initializeCore(data) {
    connectSocket();
    showNavbar();
    console.log("Initializing core methods.");
    loadCoreSettings(data);
    $('.cancelButton').cancelButton();
    console.log("Core initialized.");
}

const toggleNavbar = () => {
    const nav = document.getElementById('nav-bar'),
        bodypd = document.getElementById('body-pd'),
        toggleEl = document.getElementById('header_toggle'),
        toggle = document.getElementById('header-toggle');
    toggle.classList.toggle('rotate');

    if (nav && bodypd) {
        nav.classList.toggle('show');
        toggleEl.classList.toggle('header-open');
        bodypd.classList.toggle('body-pd');
    }
}

const showNavbar = () => {
    const toggle = document.getElementById('header-toggle'), nav = document.getElementById('nav-bar');
    //toggleNavbar();
    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            toggleNavbar();
        });
    }
}

const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

function loadCoreSettings(data) {
    const settingsButton = $("#settingsButton");
    if (data["show_settings"]) {
        settingsButton.hide();
    } else {
        settingsButton.show();
    }

    const logoutButton = $("#signOutButton");
    logoutButton.on("click", () => {
        // Delete "Authorization" cookie
        document.cookie = "Authorization=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";

        // Send GET request to "/logout" endpoint
        fetch("/logout", {method: "GET"})
            .then(() => {
                // Redirect user to home page
                window.location.href = "/login";
            });
    });


    if (data["user_auth"]) {
        logoutButton.show();
    } else {
        logoutButton.hide();
    }

    const logoText = document.getElementById("menuTitle");
    logoText.innerHTML = data["title"];
    document.title = data["title"];
}

// endregion


// region UiMethods

function registerImageReceiver(receiverName, callback) {
    imageReceivers[receiverName] = callback;
}

function registerMaskReceiver(receiverName, callback) {
    maskReceivers[receiverName] = callback;
}
// Show error modal on socket disconnect or other errors.
function showError(message) {
    // Set the error message in the modal body
    document.getElementById("errorModalMessage").innerHTML = message;

    // Show the modal
    $('#errorModal').modal('show');
}

function createElement(elementData, id_prefix = "", additional_classes = []) {
    if (id_prefix.indexOf("_") === -1) {
        id_prefix += "_";
    }
    
    console.log("Creating element: ", elementData);
    let type = elementData.hasOwnProperty("type") ? elementData["type"] : "";
    let key = (elementData.hasOwnProperty("key") ? elementData["key"] : "");
    if (key === "" || type === "") return null;
    let description = elementData.hasOwnProperty("description") ? elementData["description"] : "";
    // If the string contains brackets, extract the list of options from the brackets and set description to the rest
    let types = [];
    if (description.indexOf("]") !== -1) {
        types = description.substring(description.indexOf("[") + 1, description.indexOf("]")).split(",");
        description = description.substring(description.indexOf("]") + 1);
    }
    let options = false;
    if (elementData.hasOwnProperty("options")) {
        options = elementData["options"];
        type = "select";
    }
    let modelType;
    if (type.indexOf("modelSelect") !== -1) {
        console.log("Model select: ", type);
        modelType = type.split("_")[0];
        type = "modelSelect";
    }
    let newElement;
    let createLabel = true;
    let addClasses = true;

    switch(type) {
        case "text":
        case "str":
            newElement = createTextInput(key, description, elementData["value"], id_prefix);
            break;
        case "int":
        case "float":
            newElement = createNumberInput(key, description, elementData["value"], id_prefix);
            break;
        case "ConstrainedFloatValue":
        case "ConstrainedIntValue":
            createLabel = false;
            newElement = createSliderInput(key, elementData["title"], elementData["value"], elementData["min"], elementData["max"], elementData["step"], id_prefix);
            break;
        case "select":
            addClasses = false;
            newElement = createSelectInput(key, description, options, elementData["value"], id_prefix, additional_classes);
            break;
        case "bool":
            createLabel = false;
            addClasses = false;
            newElement = createCheckboxInput(key, elementData["title"], description, elementData["value"], id_prefix, additional_classes);
            break;
        case "modelSelect":
            createLabel = false;
            newElement = createModelSelectInput(key, elementData["title"], elementData["value"], modelType, id_prefix);
            break;
        default:
            console.log("Unknown element type: ", type, key);
            break;
    }

    // Enumerate options and add classes to newElement
    if (newElement){
        let skip = false;
        if (additional_classes.length > 0 && addClasses) {
            for (let i = 0; i < additional_classes.length; i++) {
                newElement.classList.add(additional_classes[i]);
            }
        }
        let formGroup = document.createElement("div");
        if (types.length > 0) {
            types.forEach(function(option) {
                option = option.trim();
                if (option === "model") {
                    skip = true;
                }
                formGroup.classList.add(option + "Only");
            });
        }
        if (skip) return null;

        formGroup.classList.add("form-group");
        if (createLabel) {
            let label = document.createElement("label");
            label.for = id_prefix + key;
            label.innerHTML = elementData["title"];
            label.title = description;
            formGroup.appendChild(label);
        }
        newElement.title = description;
        newElement.classList.add("form-control");
        formGroup.appendChild(newElement);
        return formGroup;
    }
    return null;
}


function createModelSelectInput(key, description, value, modelType, id_prefix = "") {
    let container = document.createElement("div");
    container.id = id_prefix + key;
    container.classList.add("form-group");
    $(container).modelSelect({
        model_type: modelType,
        value: value,
        label: description,
    });
    return container;
}
function createTextInput(key, description, value, id_prefix = "") {
    let input = document.createElement("input");
    input.type = "text";
    input.id = id_prefix + key;
    input.name = key;
    input.value = value;
    input.placeholder = description;
    input.classList.add("form-control");
    return input;
}

function createNumberInput(key, description, value, id_prefix = "") {
    let input = document.createElement("input");
    input.type = "number";
    input.id = id_prefix + key;
    input.name = key;
    input.value = value;
    input.placeholder = description;
    input.classList.add("form-control");
    return input;
}

function createSliderInput(key, description, value, min, max, step, id_prefix = "") {
    let container = document.createElement("div");
    container.id = id_prefix + key;
    $(container).BootstrapSlider({
        elem_id: id_prefix + key,
        min: min,
        max: max,
        step: step,
        value: value,
        label: description
    });
    return container;
}

function createSelectInput(key, description, choices, value, id_prefix = "", additional_classes) {
    let select = document.createElement("select");
    select.id = id_prefix + key;
    select.name = key;
    select.classList.add("form-control");
    if (additional_classes.length > 0) {
        for (let i = 0; i < additional_classes.length; i++) {
            select.classList.add(additional_classes[i]);
        }
    }
    for (let i = 0; i < choices.length; i++) {
        let option = document.createElement("option");
        option.value = choices[i];
        option.text = choices[i];
        if (choices[i] === value) {
            option.selected = true;
        }
        select.appendChild(option);
    }
    return select;
}

function createCheckboxInput(key, title, description, value, id_prefix = "", additionalClasses = []) {
    // Create div
    let div = document.createElement("div");
    div.classList.add("form-check", "form-switch");

    // Create checkbox
    let checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = id_prefix + key;
    checkbox.name = key;
    checkbox.value = value;
    checkbox.dataset.key = key;
    checkbox.title = description;
    checkbox.classList.add("newModelParam", "form-check-input");
    if (additionalClasses.length > 0) {
        additionalClasses.forEach(function(option) {
            checkbox.classList.add(option);
        });
    }
    if (value) { // Checks the checkbox if value is truthy
        checkbox.setAttribute('checked', true);
    }

    // Create label
    let label = document.createElement("label");
    label.setAttribute("for", id_prefix + key);
    label.classList.add("form-check-label");
    label.textContent = title;
    label.title = description;

    // Append checkbox and label to div
    div.appendChild(checkbox);
    div.appendChild(label);

    return div;
}


// Hide the error modal on socket reconnect or error clear.
function clearError() {
    // Hide the modal
    $('#errorModal').modal('hide');

    // Clear the error message in the modal body
    document.getElementById("errorModalMessage").innerHTML = "";
}


// Show selected content pane
function showPane(module_id) {
    let panes = document.querySelectorAll(".module");
    let links = document.querySelectorAll(".nav_link");
    let ht = document.getElementById("header_toggle");
    let activePane = document.getElementById(module_id);
    let activeLink = document.getElementById(module_id + "_link");
    let sectionTitle = document.getElementById("sectionTitle");
    for (let i = 0; i < panes.length; i++) {
        let pane = panes[i];
        let link = links[i];
        if (pane !== undefined) pane.classList.remove("activePane");
        if (link !== undefined) link.classList.remove("activeLink");
    }
    if (ht.classList.contains("header-open")) {
        toggleNavbar();
    }


    if (activePane) {
        console.log("Module ids: ", moduleIds);
        activePane.classList.add("activePane");
        activeLink.classList.add("activeLink");
        sectionTitle.innerHTML = moduleIds[module_id];
    }
}

// endregion


// region SocketMethods


// Send a socket message to the specified endpoint name
function sendMessage(name, data, await = true, target = null) {
    let messageId = generateMessageId();
    return new Promise((resolve, reject) => {
        let message = {
            id: messageId,
            name: name,
            data: data,
            await: await
        }
        if (target !== null) {
            message.target = target;
        }
        const maxRetries = 5;
        let retryCount = 0;

        function send() {
            if (globalSocket.readyState === WebSocket.OPEN) {
                console.log("Sending: ", message);
                globalSocket.send(JSON.stringify(message));
                clearError();
            } else {
                retryCount++;
                if (retryCount <= maxRetries) {
                    connectSocket();
                    setTimeout(send, 500);
                } else {
                    showError("Unable to communicate with websocket.");
                    reject();
                    return false;
                }
            }
        }

        if (globalSocket === null || globalSocket.readyState === WebSocket.CLOSED) {
            connectSocket();
            globalSocket.onopen = function () {
                send();
            };
        } else {
            send();
        }

        // Register a callback to handle the response message
        function handleResponse(event) {
            let response = JSON.parse(event.data);
            if (response.id === message.id) {
                const index = messages.indexOf(message.id);
                if (index > -1) {
                    messages.splice(index, 1);
                }
                // This is the response we're waiting for
                globalSocket.removeEventListener("message", handleResponse);
                console.log("Received: ", response);
                resolve(response.data);
            }
        }

        // Move the event listener registration outside the send() function
        if (await) {
            messages.push(messageId);
            globalSocket.addEventListener("message", handleResponse);
        }
    });
}


// Generate a random message ID
function generateMessageId() {
    return Math.floor(Math.random() * 1000000);
}

// Set up socket and it's event listeners
function connectSocket() {
    const authCookie = document.cookie.split(';')
        .map(cookie => cookie.trim())
        .find(cookie => cookie.startsWith('auth='));
    const isAuthExpired = authCookie && (new Date(authCookie.split('=')[1]) < new Date());

    // Reload the page if the auth cookie has expired
    if (isAuthExpired) {
        location.reload();
        return;
    }

    if (globalSocket === null || globalSocket.readyState === WebSocket.CLOSED) {
        let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        let host = window.location.hostname;
        let port = window.location.port;
        let SOCKET_URL = `${protocol}//${host}:${port}/ws`;
        globalSocket = new WebSocket(SOCKET_URL);
        globalSocket.onopen = function () {
            clearError();
        };
        globalSocket.onmessage = function (event) {
            let message;
            if (typeof event.data === 'string') {
                message = JSON.parse(event.data); // parse the message string to an object
            } else {
                message = event.data; // use the received object as-is
            }
            if (!message.hasOwnProperty("name")) {
                console.log("Event has no name property, cannot process: ", event);
                return;
            }
            const name = message.name;
            const index = messages.indexOf(message.id);
            // If it's not in the message queue or has a broadcast flag, then it's not a response to a request
            if (index > -1 && !message.hasOwnProperty("broadcast")) {
                return;
            }

            let method_name = message.name;
            if (method_name === "Received") {
                console.log("Message received: ", event);
            } else {
                if (socketMethods.hasOwnProperty(method_name)) {
                    if (method_name !== "status") console.log("Forwarding method: ", method_name, message);
                    for (let i = 0; i < socketMethods[method_name].length; i++) {
                        socketMethods[method_name][i](message);
                    }
                } else {
                    console.log("Unknown message name: ", method_name, event);
                }
            }
        };
        globalSocket.onerror = function (event) {
            if (event instanceof CloseEvent) {
                if (event.code === 403) {
                    console.log("WebSocket error: 403 Forbidden");
                    location.reload();
                } else {
                    console.log("WebSocket error: ", event);
                }
            } else {
                console.log("WebSocket error: ", event);
            }
        };
        globalSocket.onclose = function (event) {
            console.log("WebSocket disconnected with code: ", event.code);
            showError("Websocket Disconnected, attempting reconnect...");
            if (event.code === 1000 || event.code === 403) {
                location.reload();
            } else {
                setTimeout(function () {
                    connectSocket();
                }, 2000);
            }
        };

    }
}


// endregion


// region RegistrationMethods

// Register an extension in the menu
function registerExtension(module_name, module_id, module_icon) {

    let navList = document.getElementById("extensionList");
    let existingModule = document.getElementById(module_id);
    let newModule;

    if (existingModule) {
        navList.removeChild(existingModule);
    }

    newModule = document.createElement("a");
    newModule.href = "#";
    newModule.className = "nav_link";
    newModule.id = module_id;

    let icon = document.createElement("i");
    icon.className = `bx bx-${module_icon} nav_icon`;

    let name = document.createElement("span");
    name.className = "nav_name";
    name.textContent = module_name;

    newModule.appendChild(icon);
    newModule.appendChild(name);
    navList.appendChild(newModule);

    newModule.addEventListener("click", function () {
        showPane(module_id);
    });
}


// Register a socket call
function registerSocketMethod(extension_name, method, callback) {
    if (!socketMethods[method]) {
        socketMethods[method] = [];
    }
    socketMethods[method].push(callback);
}


// Deregister an extension from the menu
function DeregisterExtension(module_id) {
    let navList = document.getElementById("extensionList");
    let existingModule = document.getElementById(module_id);
    if (existingModule) {
        navList.removeChild(existingModule);
    }
}

// Remove socket call from listener
function deRegisterSocketMethod(extension_name, method) {
    if (socketMethods.hasOwnProperty(extension_name + "" + method)) {
        delete socketMethods[extension_name + "" + method];
    }
}

// endregion

// region helperFunctions
const generateRandomString = (length) => {
    const characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let result = "";
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * characters.length));
    }
    return result;
};

// endregion

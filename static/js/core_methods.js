let globalSocket = null;
let socketMethods = {};

const keyListener = new KeyListener();
const historyTracker = new HistoryTracker();
console.log("History tracker initialized.");
let messages = [];
// region Initialization

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
    toggleNavbar();
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


document.addEventListener("DOMContentLoaded", function () {
    connectSocket();

    showNavbar();
    sendMessage("get_config", {"section_key": "core"}).then((data) => {
        loadCoreSettings(data);
    });
    const $buttons = $('.cancelButton').cancelButton();
});

function loadCoreSettings(data) {
    console.log("Got core settings: ", data);
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

// Show error modal on socket disconnect or other errors.
function showError(message) {
    // Set the error message in the modal body
    document.getElementById("errorModalMessage").innerHTML = message;

    // Show the modal
    $('#errorModal').modal('show');
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
                    console.log("Connecting socket: " + retryCount + "/" + maxRetries);
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
            if (name !== "status") {
                console.log("Got message: ", name, message);
            }
            const index = messages.indexOf(message.id);
            if (index > -1 && !message.hasOwnProperty("broadcast")) {
                console.log("NO message ID or broadcast: ", message);
                return;
            }

            let method_name = message.name;
            console.log("Got message: ", method_name);
            if (method_name === "Received") {
                console.log("Message received: ", event);
            } else {
                if (socketMethods.hasOwnProperty(method_name)) {
                    console.log("Forwarding method: ", method_name, message);
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

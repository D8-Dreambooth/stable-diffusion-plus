let globalSocket = null;
let socketMethods = {};
const SOCKET_URL = "ws://localhost:8080/ws";

// region Initialization

document.addEventListener("DOMContentLoaded", function () {
    // Set up socket
    connectSocket();
    // Navbar toggle listener
    const showNavbar = (toggleId, navId, bodyId, headerId) => {
        const toggle = document.getElementById(toggleId),
            nav = document.getElementById(navId),
            bodypd = document.getElementById(bodyId),
            headerpd = document.getElementById(headerId)

        if (toggle && nav && bodypd && headerpd) {
            console.log("Adding toggle listener...");
            toggle.addEventListener('click', () => {
                nav.classList.toggle('show')
                toggle.classList.toggle('bx-x')
                bodypd.classList.toggle('body-pd')
                headerpd.classList.toggle('body-pd')
            })
        }
    }

    showNavbar('header-toggle', 'nav-bar', 'body-pd', 'header')


});

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
    let activePane = document.getElementById(module_id);
    let activeLink = document.getElementById(module_id + "_link");

    for (let i = 0; i < panes.length; i++) {
        console.log("Removing class: ", panes[i]);
        panes[i].classList.remove("activePane");
        links[i].classList.remove("activeLink");
    }

    if (activePane) {
        activePane.classList.add("activePane");
        activeLink.classList.add("activeLink");
        console.log("Activating:", activePane);
    }
}

// endregion


// region SocketMethods


// Send a socket message to the specified endpoint name
function sendMessage(name, data, await=true) {
    return new Promise((resolve, reject) => {
        console.log("Message request: ", name, data);
        let message = {
            id: generateMessageId(),
            name: name,
            data: data
        }

        console.log("Sending socket message: ", message);
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
                    console.log("No socket connection, reconnecting and retrying...");
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
            console.log("WebSocket not connected, connecting...");
            connectSocket();
            globalSocket.onopen = function () {
                console.log("WebSocket connected");
                send();
            };
        } else {
            send();
        }

        // Register a callback to handle the response message
        function handleResponse(event) {
            console.log("Received response: ", event);
            let response = JSON.parse(event.data);
            if (response.id === message.id) {
                // This is the response we're waiting for
                globalSocket.removeEventListener("message", handleResponse);
                console.log("Returning response:", response);
                resolve(response);
            }
        }

        // Move the event listener registration outside the send() function
        if (await) {
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
    if (globalSocket === null || globalSocket.readyState === WebSocket.CLOSED) {
        globalSocket = new WebSocket(SOCKET_URL);
        globalSocket.onopen = function () {
            clearError();
            console.log("WebSocket connected");
        };
        globalSocket.onmessage = function (event) {
            let message;
            if (typeof event.data === 'string') {
                message = JSON.parse(event.data); // parse the message string to an object
            } else {
                message = event.data; // use the received object as-is
            }
            event = message;
            console.log("Message: ", message);
            if (event.hasOwnProperty("name")) {
                let method_name = event.name;
                if (socketMethods.hasOwnProperty(method_name)) {
                    console.log("Forwarding method: ", method_name, event);
                    for (let i = 0; i < socketMethods[method_name].length; i++) {
                        console.log("Forwarding method: ", method_name, event);
                        socketMethods[method_name][i](event);
                    }
                } else {
                    console.log("Unknown message name: ", method_name, event);
                }
            } else {
                console.log("Event has no name property, can't process: ", event);
            }
        };
        globalSocket.onclose = function () {
            console.log("WebSocket disconnected");
            showError("Websocket Disconnected, attempting reconnect...");
            setTimeout(function () {
                console.log("Reconnecting to WebSocket...");
                connectSocket();
            }, 2000);
        };
    }
}

// endregion


// region RegistrationMethods

// Register an extension in the menu
function registerExtension(module_name, module_id, module_icon) {
    console.log("Register extension: ", module_name, module_id);

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
    console.log("Deregister extension: ", module_id);

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

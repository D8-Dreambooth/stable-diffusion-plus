let globalSocket = null;
let socketMethods = {};
const SOCKET_URL = "ws://localhost:8080/ws";

// region Initialization

document.addEventListener("DOMContentLoaded", function () {

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

    // Set up socket
    connectSocket();
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
function sendMessage(name, data) {
    let message = {
        type: name,
        data: data
    }

    console.log("Sending socket message: ", message);
    if (globalSocket.readyState !== WebSocket.OPEN) {
        connectSocket();
    }
    if (globalSocket.readyState === WebSocket.OPEN) {
        globalSocket.send(JSON.stringify(message));
        clearError();
    } else {
        showError("Unable to communicate with websocket.");
    }
}

// Set up socket and it's event listeners
function connectSocket() {
    if (globalSocket === null || globalSocket.readyState === WebSocket.CLOSED) {
        globalSocket = new WebSocket(SOCKET_URL);
        globalSocket.onopen = function() {
            clearError();
            console.log("WebSocket connected");
        };
        globalSocket.onmessage = function (event) {
            console.log("MESSAGE: ", event);
            if (event.hasOwnProperty("name")) {
                let method_name = event.name;
                if (socketMethods.hasOwnProperty(method_name)) {
                    socketMethods[method_name](event);
                }
            }
        };
        globalSocket.onclose = function() {
            console.log("WebSocket disconnected");
            showError("Websocket Disconnected, attempting reconnect...");
            setTimeout(function() {
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

    newModule.addEventListener("click", function() {
        showPane(module_id);
    });
}


// Register a socket call
function registerSocketMethod(extension_name, method, callback) {
    socketMethods[extension_name + "_" + method] = callback;
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

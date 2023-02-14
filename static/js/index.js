let globalSocket;
let socketMethods = {};
const SOCKET_URL = "ws://localhost:8080/ws";
document.addEventListener("DOMContentLoaded", function (event) {

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

    /*===== LINK ACTIVE =====*/
    const linkColor = document.querySelectorAll('.nav_link')

    function colorLink() {
        if (linkColor) {
            linkColor.forEach(l => l.classList.remove('active'))
            this.classList.add('active')
        }
    }

    linkColor.forEach(l => l.addEventListener('click', colorLink))
    globalSocket = new WebSocket(SOCKET_URL);
    globalSocket.onmessage = function (event) {
        console.log("MESSAGE: ", event);
        if (event.hasOwnProperty("name")) {
            let method_name = event.name;
            if (socketMethods.hasOwnProperty(method_name)) {
                socketMethods[method_name](event);
            }
        }
    };
});


function sendMessage(name, data) {
    let message = {
        type: name,
        data: data
    }

    console.log("Sending socket message: ", message);
    if (globalSocket.readyState === WebSocket.OPEN) {
        globalSocket.send(JSON.stringify(message));
    } else {
        checkConnection();
    }
}

function checkConnection() {
    console.log("Checking connection...");
    if (globalSocket.readyState === WebSocket.CLOSED) {
        console.log("Reconnecting to WebSocket...");
        globalSocket = new WebSocket(SOCKET_URL);
        setTimeout(checkConnection, 2000);
    }
}

function registerModule(module_name, module_id, module_icon) {
    console.log("Register module: ", module_name, module_id);

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



function registerSocketMethod(extension_name, method, callback) {
    socketMethods[extension_name + "_" + method] = callback;
}

function deRegisterSocketMethod(extension_name, method) {
    if (socketMethods.hasOwnProperty(extension_name + "" + method)) {
        delete socketMethods[extension_name + "" + method];
    }
}

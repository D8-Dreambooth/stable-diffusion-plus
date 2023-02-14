// A set of JS methods that are loaded *after* extensions, so they are only available to native modules


// region RegistrationMethods

// Register a UI Module in the menu
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

// Deregister a UI Module from the menu
function DeregisterModule(module_id) {
    console.log("Deregister module: ", module_id);

    let navList = document.getElementById("navList");
    let existingModule = document.getElementById(module_id + "_link");

    if (existingModule) {
        navList.removeChild(existingModule);
    }
}

// endregion

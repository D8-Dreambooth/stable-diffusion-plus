// A set of JS methods that are loaded *after* extensions, so they are only available to native modules
let moduleIds = {};

// region RegistrationMethods

// Register a UI Module in the menu
function registerModule(module_name, module_id, module_icon, is_default = false, index=-1) {
    console.log("Register module: ", module_name, module_id, index);

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

    newModule.addEventListener("click", function() {
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
                return 1; // Append a to the end
            }
        } else if (bIndex === -1) {
            return -1; // Append b to the end
        } else {
            return aIndex - bIndex;
        }
    });

    // Re-add sorted navLinks to navList
    navList.innerHTML = "";
    for (let link of navLinks) {
        navList.appendChild(link);
    }
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

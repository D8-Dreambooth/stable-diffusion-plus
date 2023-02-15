class FileBrowser {
    constructor(parentElement,
                showSelectButton = false,
                listFiles = false,
                placeholder="Select something...",
                expand = false) {
        this.parentElement = parentElement;
        this.placeholder = placeholder;
        this.endpoint = "files"
        this.showSelectButton = showSelectButton;
        this.currentPath = "";
        this.currentParent = "";
        this.selectedLink = undefined;
        this.listFiles = listFiles;
        this.treeContainer = document.createElement("div");
        this.treeContainer.classList.add("tree");
        this.treeParent = document.createElement("div");
        this.treeParent.classList.add("tree-container");
        this.expanded = expand;
        if (expand) {
            this.treeParent.classList.add("full");
        }
        this.buildInput();


        this.buildTree().then(() => {
            this.treeParent.appendChild(this.treeContainer);

            if (this.showSelectButton) {
                const selectButton = document.createElement("button");
                selectButton.classList.add("btn", "btn-primary");
                selectButton.textContent = "Select";
                selectButton.addEventListener("click", () => {
                    if (this.selectedLink !== undefined) {
                        this.currentPath = this.selectedLink.dataset.path;
                        let base = this.currentParent === this.separator ? this.currentParent : this.currentParent + this.separator;
                        this.input.value = base + this.currentPath;
                        this.toggleTree();
                    }
                });
                const cancelButton = document.createElement("button");
                cancelButton.classList.add("btn", "btn-secondary");
                cancelButton.textContent = "Cancel  ";
                cancelButton.addEventListener("click", () => {
                    this.toggleTree();
                });
                const btnGroup = document.createElement("div");
                btnGroup.classList.add("btn-group", "file-buttons");
                btnGroup.appendChild(selectButton);
                btnGroup.appendChild(cancelButton);
                this.treeParent.appendChild(btnGroup);

            }
            this.parentElement.appendChild(this.treeParent);

        });

        this.onDoubleClickCallbacks = [];
        this.onClickCallbacks = [];
        this.onSelectCallbacks = [];
        this.onCancelCallbacks = [];
        this.selected = "";
    }

    buildInput() {
        const inputGroup = document.createElement("div");
        inputGroup.classList.add("input-group");
        const input = document.createElement("input");
        input.classList.add("form-control");
        input.type = "text";
        input.placeholder = this.placeholder;
        this.input = input;
        inputGroup.appendChild(input);

        const toggleButton = document.createElement("button");
        toggleButton.classList.add("btn", "btn-secondary");

        toggleButton.innerHTML = this.expanded ? `<i class="fas fa-chevron-up"></i>` : `<i class="fas fa-chevron-down"></i>`;
        inputGroup.appendChild(toggleButton);
        toggleButton.addEventListener("click", () => {
            this.toggleTree();
        });
        this.toggleButton = toggleButton;
        this.parentElement.appendChild(inputGroup);
    }

    toggleTree() {
        this.treeParent.classList.toggle("full");
        this.expanded = this.treeParent.classList.contains("full");
        this.toggleButton.innerHTML = this.expanded ? `<i class="fas fa-chevron-up"></i>` : `<i class="fas fa-chevron-down"></i>`;
    }

    async buildTree() {
        const response = await this.fetchFileTreeData(this.currentPath);
        console.log("Build tree res: ", response);
        let items = response["items"] || [];
        this.currentParent = response["current"] || "";
        this.separator = response["separator"] || "\\";
        const tree = this.generateTree(items);
        this.treeContainer.innerHTML = "";
        let title = document.createElement("span");
        title.innerHTML = "File Browser";
        title.classList.add("fileTitle");
        let currentPath = document.createElement("span");
        currentPath.innerHTML = this.currentParent;
        currentPath.classList.add("fileCurrent");
        this.treeContainer.appendChild(title);
        this.treeContainer.appendChild(currentPath);
        this.treeContainer.appendChild(tree);
        if (this.showSelectButton) {

        }
        this.attachEventHandlers();
    }

    generateTree(response) {
        console.log("Parsing response: ", response);
        const root = document.createElement("ul");
        const listItem = document.createElement("li");
        const icon = document.createElement("i");
        icon.classList.add("bx", "bx-hdd", "fileIcon");
        listItem.appendChild(icon);
        listItem.classList.add("fileLi");
        const link = document.createElement("a");
        link.innerHTML = "..";
        listItem.dataset.path = "..";
        listItem.dataset.type = "directory";
        listItem.appendChild(link);
        root.appendChild(listItem);
        for (const [path, details] of Object.entries(response)) {
            console.log("Path, details: ", path, details);
            const [dateModified, size, type, children] = details;
            const splitPath = path.split("/");

            if (splitPath.length === 1) {
                const listItem = document.createElement("li");
                listItem.classList.add("fileLi");
                listItem.dataset.path = path;
                listItem.dataset.type = type;
                listItem.dataset.date = dateModified;
                listItem.dataset.size = size;

                const icon = document.createElement("i");
                const iconClass = this.getClass(type);
                icon.classList.add("bx", iconClass, "fileIcon");
                listItem.appendChild(icon);
                const link = document.createElement("a");
                link.innerHTML = splitPath[0];
                listItem.appendChild(link);
                if (children) {
                    const childList = document.createElement("ul");
                    listItem.appendChild(childList);
                }
                root.appendChild(listItem);
            } else if (splitPath.length === 2) {
                const parentPath = splitPath[0];
                const currentPath = splitPath[1];
                const parentElement = root.querySelector(
                    `a[data-path="${parentPath}"]`
                ).parentElement;
                const listItem = document.createElement("li");
                listItem.dataset.path = path;
                listItem.dataset.type = type;
                listItem.dataset.date = dateModified;
                listItem.dataset.size = size;
                const link = document.createElement("a");
                link.innerHTML = currentPath;
                listItem.appendChild(link);
                if (children) {
                    const childList = document.createElement("ul");
                    listItem.appendChild(childList);
                }
                parentElement.querySelector("ul").appendChild(listItem);
            }
        }
        return root;
    }

    attachEventHandlers() {
        const allLinks = this.treeContainer.querySelectorAll(".fileLi");
        console.log("Links: ", allLinks);
        allLinks.forEach((link) => {
            if (link.dataset.path) {
                link.addEventListener("dblclick", () => {
                    console.log("DBL: ", link);
                    if (link.dataset.type === "directory") {
                        this.currentPath = link.dataset.path;
                        this.buildTree();
                    }

                    this.onDoubleClickCallbacks.forEach((callback) =>
                        callback(link.dataset.path, link.dataset.type)
                    );
                });
                link.addEventListener("click", () => {
                    console.log("Click: ", link);
                    this.selectLink(link);
                    this.onClickCallbacks.forEach((callback) =>
                        callback(link.dataset.path)
                    );
                });
            } else {
                console.log("No path: ", link);
            }
        });
        const selectButton = this.treeContainer.querySelector(".fileSelect");
    }

    selectLink(link) {
        const allLinks = this.treeContainer.querySelectorAll(".fileLi");
        allLinks.forEach((cLink) => {
            cLink.classList.remove("selected");
        });

        link.classList.add("selected");
        console.log("Link selected: ", link.dataset);
        this.selectedLink = link;
    }

    getClass(type) {
        console.log("Let's get an icon: ", type);
        switch (type) {
            case '.jpg':
            case '.jpeg':
                return 'bxs-file-jpg';
            case '.gif':
                return 'bxs-file-gif';
            case '.png':
                return 'bxs-file-png';
            case '.txt':
                return 'bxs-file-txt';
            case '.md':
                return 'bxs-file-md';
            case '.json':
                return 'bxs-file-json';
            case '.zip':
            case '.rar':
            case '.tar':
            case '.gz':
                return 'bxs-file-archive';
            case '.ckpt':
            case '.safetensors':
            case '.bin':
            case '.pt':
                return 'bx-data';
            case 'directory':
                return 'bx-folder';
            default:
                return 'bx-file-blank';
        }
    }

    async fetchFileTreeData(directory, recursive = false, filter = []) {
        const data = {
            start_dir: directory,
            include_files: this.listFiles,
            recursive: recursive,
            filter: filter
        };
        console.log("Requesting tree data...");
        const response = await sendMessage(this.endpoint, data);
        console.log("Response received:", response);
        return response;
    }

    async refresh() {
        const fileTreeData = await this.fetchFileTreeData(this.currentPath);
        const tree = this.generateTree(fileTreeData);
        this.treeContainer.innerHTML = '';
        this.treeContainer.appendChild(tree);
    }

    setCurrentPath(path) {
        this.currentPath = path;
        this.refresh();
    }

    addOnDoubleClick(callback) {
        this.onDoubleClickCallbacks.push(callback);
    }

    addOnClick(callback) {
        this.onClickCallbacks.push(callback);
    }

    addOnSelect(callback) {
        this.onSelectCallbacks.push(callback);
    }

    addOnCancel(callback) {
        this.onCancelCallbacks.push(callback);
    }

}

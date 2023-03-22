class FileBrowser {
    constructor(parentElement, options = {}) {
        this.onDoubleClickCallbacks = [];
        this.onClickCallbacks = [];
        this.onSelectCallbacks = [];
        this.onCancelCallbacks = [];
        this.selected = "";
        let wrapper = document.createElement("div");
        wrapper.classList.add("row", "fileBrowserContainer");
        parentElement.appendChild(wrapper);
        this.parentElement = wrapper;
        this.infoPanel = undefined;
        this.endpoint = "files";
        this.fileEndpoint = "file";
        this.currentPath = "";
        this.currentParent = "";
        this.selectedLink = undefined;
        console.log("Options: ", options);
        this.treeContainer = document.createElement("div");
        this.treeContainer.classList.add("tree");
        this.treeParent = document.createElement("div");
        this.treeParent.classList.add("tree-container", "col-6");
        this.placeholder = options["placeholder"] || "Select something...";
        this.showSelectButton = options["showSelectButton"] || false;
        this.listFiles = options["listFiles"] || false;
        this.expanded = options["expand"] || false;
        this.multiselect = options["multiselect"] || false;
        this.dropdown = options["dropdown"] !== undefined ? options["dropdown"] : false;
        this.showTitle = options["showTitle"] !== undefined ? options["showTitle"] : true;
        this.showInfo = options["showInfo"] !== undefined ? options["showInfo"] : true;
        this.style = options["style"] !== undefined ? options["style"] : "";
        if (this.expanded) {
            this.treeParent.classList.add("full");
        }
        if (this.style !== "") {
            this.treeParent.style.cssText = this.style;
        }



        this.buildTree().then(() => {
            let inputGroup = this.buildInput();
            this.parentElement.prepend(inputGroup);
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
            this.parentElement.append(this.treeParent);
            if (this.showInfo) {
                this.onClickCallbacks.push(this.showFileInfo);
                this.infoPanel = document.createElement("div");
                this.infoPanel.classList.add("infoPanel", "closed", "col-6");
                this.parentElement.appendChild(this.infoPanel);
            }
        });


    }

    buildInfoPanel(fileInfo) {
        console.log("Building: ", fileInfo);
        const panelContainer = document.createElement("div");
        panelContainer.classList.add("row");

        // File info panel
        const infoPanel = document.createElement("div");
        infoPanel.classList.add("col-12");
        const infoList = document.createElement("ul");
        infoList.classList.add("list-group", "list-group-flush");
        const filename = document.createElement("li");
        filename.classList.add("list-group-item", "active");
        filename.textContent = fileInfo.filename;
        infoList.appendChild(filename);
        const created = document.createElement("li");
        created.classList.add("list-group-item");
        created.textContent = `Created: ${fileInfo.date_created}`;
        infoList.appendChild(created);
        const modified = document.createElement("li");
        modified.classList.add("list-group-item");
        modified.textContent = `Modified: ${fileInfo.date_modified}`;
        infoList.appendChild(modified);
        const size = document.createElement("li");
        size.classList.add("list-group-item");
        size.textContent = `Size: ${fileInfo.size}`;
        infoList.appendChild(size);
        infoPanel.appendChild(infoList);
        panelContainer.appendChild(infoPanel);

        // Image panel
        if (fileInfo.src) {
            const imgPanel = document.createElement("div");
            imgPanel.classList.add("col-12");
            const img = document.createElement("img");
            img.classList.add("img-fluid", "img-thumbnail");
            img.src = fileInfo.src;
            imgPanel.appendChild(img);
            panelContainer.appendChild(imgPanel);
        }

        // Data panel
        if (fileInfo.data) {
            const dataPanel = document.createElement("div");
            dataPanel.classList.add("col-12", "mt-3", "dataPanel");
            const pre = document.createElement("pre");
            pre.classList.add("bg-light", "p-3", "border");
            pre.textContent = fileInfo.data;
            dataPanel.appendChild(pre);
            if (fileInfo.src) {
                panelContainer.appendChild(dataPanel);
            } else {
                const dataWrapper = document.createElement("div");
                dataWrapper.classList.add("col-12");
                dataWrapper.appendChild(dataPanel);
                panelContainer.appendChild(dataWrapper);
            }
        }

        return panelContainer;
    }




    buildInput() {
        const inputGroup = document.createElement("div");
        inputGroup.classList.add("input-group");
        if (this.dropdown) {
            console.log("Dropdown enabled.");
        } else {
            console.log("Hide dropdown.")
            inputGroup.classList.add("hide");
        }
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
        return inputGroup;
    }

    toggleTree() {
        this.treeParent.classList.toggle("full");
        this.infoPanel.classList.toggle("closed");
        this.expanded = this.treeParent.classList.contains("full");
        this.toggleButton.innerHTML = this.expanded ? `<i class="fas fa-chevron-up"></i>` : `<i class="fas fa-chevron-down"></i>`;
    }

    async buildTree() {
        const response = await this.fetchFileTreeData(this.currentPath);
        let items = response["items"] || [];
        this.currentParent = response["current"] || "";
        this.separator = response["separator"] || "\\";
        const tree = this.generateTree(items);
        this.treeContainer.innerHTML = "";
        if (this.showTitle) {
            let title = document.createElement("span");
            title.innerHTML = "File Browser";
            title.classList.add("fileTitle");
            this.treeContainer.appendChild(title);
        }

        let currentPath = document.createElement("span");
        currentPath.innerHTML = this.currentParent;
        currentPath.classList.add("fileCurrent");

        this.treeContainer.appendChild(currentPath);
        this.treeContainer.appendChild(tree);
        if (this.showSelectButton) {

        }
        this.attachEventHandlers();
    }

    generateTree(response) {
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
        let startLink;
        allLinks.forEach((link) => {
            if (link.dataset.path) {
                link.addEventListener("dblclick", () => {
                    if (link.dataset.type === "directory") {
                        this.currentPath = link.dataset.path;
                        this.buildTree();
                    }
                    this.onDoubleClickCallbacks.forEach((callback) =>
                        callback(link.dataset.path, link.dataset.type)
                    );
                });
                link.addEventListener("click", (event) => {
                    if (event.ctrlKey) {
                        // Control key is pressed
                        if (!this.selectedLinks.includes(link)) {
                            this.selectedLinks.push(link);
                        }
                    } else if (event.shiftKey) {
                        // Shift key is pressed
                        if (this.selectedLinks.length > 0) {
                            const currentIndex = Array.from(allLinks).indexOf(link);
                            const startIndex = Array.from(allLinks).indexOf(startLink);
                            const [minIndex, maxIndex] = [currentIndex, startIndex].sort((a, b) => a - b);
                            for (let i = minIndex; i <= maxIndex; i++) {
                                const selectedLink = allLinks[i];
                                if (!this.selectedLinks.includes(selectedLink)) {
                                    this.selectedLinks.push(selectedLink);
                                    selectedLink.classList.add("selected");
                                }
                            }
                        }
                    } else {
                        // Neither control nor shift key is pressed
                        startLink = link;
                        this.selectedLinks = [link];
                        allLinks.forEach((cLink) => {
                            cLink.classList.remove("selected");
                        });
                        link.classList.add("selected");
                    }
                    this.onClickCallbacks.forEach((callback) =>
                        callback.call(this, link, link.dataset.path, link.dataset.type)
                    );
                });
            } else {
                console.log("No path: ", link);
            }
        });

    }


    getClass(type) {
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
        const response = await sendMessage(this.endpoint, data);
        console.log("Response received:", response);
        return response;
    }

    showFileInfo(link, data1, data2) {
        console.log("File info: ", link, data1, data2);
        this.fetchFileData(data1).then((data) =>{
            console.log("SHOW: ", data);
            let panel = this.buildInfoPanel(data[0]);
            console.log("PANEL: ", panel);
            this.infoPanel.innerHTML = panel.innerHTML;
            if (this.infoPanel.classList.contains("closed")) {
                this.infoPanel.classList.remove("closed");
                this.treeParent.classList.add("full", "hasInfo");
            }
        });
    }
    async fetchFileData(file) {
        console.log("FFD: ", file);
        const data = {
            files: file
        };
        const response = await sendMessage(this.fileEndpoint, data);
        console.log("Response received:", response);
        if (response.hasOwnProperty("files")) {
            return response.files;
        }
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

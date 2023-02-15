class FileBrowser {
    constructor(parentElement, showSelectButton = false, listFiles = false) {
        this.parentElement = parentElement;
        this.endpoint = "files"
        this.showSelectButton = showSelectButton;
        this.currentPath = "";
        this.listFiles = listFiles;
        this.treeContainer = document.createElement("div");
        this.treeContainer.classList.add("tree");
        this.parentElement.appendChild(this.treeContainer);
        this.buildTree().then();
        this.onDoubleClickCallbacks = [];
        this.onClickCallbacks = [];
        this.onSelectCallbacks = [];
        this.onCancelCallbacks = [];
        this.selected = "";
    }

    async buildTree() {
        const response = await this.fetchFileTreeData(this.currentPath);
        console.log("Build tree res: ", response);
        let items = response["items"] || [];
        let current = response["current"] || "";
        const tree = this.generateTree(items);
        this.treeContainer.innerHTML = "";
        let title = document.createElement("span");
        title.innerHTML = "File Browser";
        title.classList.add("fileTitle");
        let currentPath = document.createElement("span");
        currentPath.innerHTML = current;
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
        this.selected = link;
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

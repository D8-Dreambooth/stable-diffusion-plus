class InlineGallery {
    constructor(parentElement, options = {}) {
        this.container = parentElement;
        this.currentElements = options["data"] || [];
        this.loaded = false;

        // See https://fotorama.io/docs/4/options/ for full list of options.
        this.gallery_options = Object.assign({
            width: '100%',
            maxheight: "300px",
            allowfullscreen: true,
            nav: 'thumbs',
            loop: true,
            fit: "contain",
            transition: 'crossfade',
            transitionduration: 400,
            data: this.mapElements(),
            ...options
        });

        this.createFotorama();
        registerSocketMethod("status", "status", this.socketUpdate.bind(this));
    }

    createFotorama() {
        this.gallery = $(this.container).fotorama(this.gallery_options);
        this.fotoramaInstance = this.gallery.data('fotorama');
        this.loaded = true;
    }

    addDownloadButton() {
        let fotoramaStage = this.container.querySelector('.fotorama__stage');

        if (fotoramaStage && !fotoramaStage.querySelector('.fotorama__download-icon')) {
            let downloadIcon = document.createElement('div');
            downloadIcon.classList.add('fotorama__download-icon', 'bx', 'bxs-download');
            downloadIcon.tabIndex = 2;
            downloadIcon.addEventListener('click', this.onDownloadButtonClick.bind(this));
            fotoramaStage.appendChild(downloadIcon);
        }
    }

    onDownloadButtonClick() {
        let activeFrame = this.fotoramaInstance.activeFrame;
        console.log("DL Click.");
        if (activeFrame) {
            console.log("Got active.");
            let downloadLink = document.createElement('a');
            downloadLink.href = activeFrame.img;
            downloadLink.download = 'image.jpg';
            downloadLink.click();
        }
    }


    socketUpdate(data) {
        console.log("Got status: ", data);
        const formatted = this.extractImageData(data);
        console.log("Formatted: ", formatted);
        this.update(formatted, false);
    }

    extractImageData(data) {
        const status = data.status;
        if (!status || !status.images || !status.images.length) {
            return [];
        }

        const images = status.images;
        const descriptions = status.descriptions || [];
        const prompts = status.prompts || [];

        const imageList = [];
        for (let i = 0; i < images.length; i++) {
            const imagePath = images[i];

            let caption = '';
            if (prompts.length > i && typeof prompts[i] === 'string') {
                caption = prompts[i];
            }

            let description = '';
            if (descriptions.length > i && typeof descriptions[i] === 'string') {
                description = descriptions[i];
            }

            imageList.push({path: imagePath, caption: caption, description: description});
        }

        return imageList;
    }

    update(newItems, append = false) {
        console.log("Updated: ", newItems);
        let updatedDynamicElements;
        if (append) {
            updatedDynamicElements = [...this.currentElements, ...newItems];
        } else {
            updatedDynamicElements = newItems;
        }

        this.currentElements = updatedDynamicElements;
        let dynamicElements = this.mapElements();

        if (this.loaded) {
            this.fotoramaInstance.load(dynamicElements);
            this.addDownloadButton();
        }
    }

    mapElements() {
        return this.currentElements.map((element) => {
            let src = element.path;
            if (src.indexOf("http://") === -1 && src.indexOf("https://") === -1) {
                src = "data:image/png;base64, " + src;
            }
            let cap = element.caption;
            let desc = element.description;

            return {
                img: src,
                thumb: src,
                caption: cap,
                description: desc
            };
        });
    }

    clear() {
        if (this.loaded) {
            console.log("Clearing!");
            this.currentElements = [];
            this.loaded = false;
            this.fotoramaInstance.destroy();
            this.createFotorama();
        }
    }
}

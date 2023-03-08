class InlineGallery {
    constructor(parentElement, options = {}) {
        this.container = parentElement;
        this.currentElements = options["data"] || [];
        this.showMaximizeIcon = options["show_maximize"] || true;
        this.closable = options["closable"] || false;
        this.thumbnail = options["thumbnail"] || true;
        this.start_open = options["start_open"] || true;
        this.loaded = false;

        // See https://www.lightgalleryjs.com/docs/settings/ for full list of options.
        this.gallery_options = Object.assign({
            container: this.container,
            dynamic: true,
            hash: false,
            closable: this.closable,
            thumbnail: this.thumbnail,
            showMaximizeIcon: this.showMaximizeIcon,
            plugins: [lgZoom, lgThumbnail, lgFullscreen],
            appendSubHtmlTo: '.lg-item',
            slideDelay: 400,
            dynamicEl: this.mapElements(),
            ...options
        });

        // This is not redundant.
        this.gallery = lightGallery(this.container, this.gallery_options);

        // We normally want this for our use-case
        if (this.start_open) {
            this.openGallery();
        }
        registerSocketMethod("status", "status", this.socketUpdate.bind(this));
    }

    socketUpdate(data) {
        console.log("Got status: ", data);
        const formatted = this.extractImageData(data);
        console.log("Formatted: ", formatted);
        this.update(formatted,false);
    }

    extractImageData(data) {
        const status = data.status;
        if (!status || !status.images || !status.images.length) {
            return [];
        }

        const images = status.images;
        console.log("We have " + images.length + " images.")
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


    openGallery() {
        if (this.currentElements.length > 0) {
            try {
                this.gallery.openGallery();
            } catch {

            }
        }
    }

    update(newItems, append = false) {
        console.log("Updated: ", newItems);
        let doUpdate = false;
        if (this.currentElements.length === 0) {
            doUpdate = true;
        }
        let updatedDynamicElements;
        if (append) {
            updatedDynamicElements = [...this.currentElements, ...newItems];
        } else {
            updatedDynamicElements = newItems;
        }

        this.currentElements = updatedDynamicElements;
        let dynamicElements = this.mapElements();
        console.log("Refreshing: ", dynamicElements);

        this.gallery_options.dynamicEl = dynamicElements;
        if (doUpdate) {
            this.gallery.destroy();
            setTimeout(() => {
                this.loaded = true;
                this.gallery = lightGallery(this.container, this.gallery_options);
                if (updatedDynamicElements.length > 0) {
                    this.gallery.openGallery();
                }
            }, 500);
        } else {
            this.loaded = true;
            this.gallery.refresh(dynamicElements);
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
            src: src,
            thumb: src,
            subHtml: `<div class="lightGallery-captions">
            <h4>${cap}</h4>
            <p>${desc}</p>
        </div>`
        };
    });
}


    clear() {
        if (this.loaded) {
            console.log("Clearing!");
            this.currentElements = [];
            this.loaded = false;
        }
    }
}

class InlineGallery {
    constructor(parentElement, options = {}) {
        this.container = parentElement;
        this.currentElements = options["data"] || [];
        this.showMaximizeIcon = options["show_maximize"] || true;
        this.closable = options["closable"] || false;
        this.thumbnail = options["thumbnail"] || true;
        this.start_open = options["start_open"] || true;

        // See https://www.lightgalleryjs.com/docs/settings/ for full list of options.
        const gallery_options = Object.assign({
            container: this.container,
            dynamic: true,
            hash: false,
            closable: this.closable,
            thumbnail: this.thumbnail,
            showMaximizeIcon: this.showMaximizeIcon,
            plugins: [lgZoom, lgThumbnail, lgFullscreen],
            appendSubHtmlTo: '.lg-item',
            slideDelay: 400,
            dynamicEl: [],
            ...options
        });

        // This is probably redundant
        if (this.currentElements.length > 0) {
            gallery_options.dynamicEl = this.currentElements.map((element) => ({
                src: element.path,
                thumb: element.path,
                subHtml: `<div class="lightGallery-captions">
          <h4>${element.caption}</h4>
          <p>${element.description}</p>
        </div>`,
            }));
        }

        // This is not redundant.
        this.gallery = lightGallery(this.container, gallery_options);

        // We normally want this for our use-case
        if (this.start_open) {
            this.openGallery();
        }
        registerSocketMethod("status", "status", this.socketUpdate);
    }

    socketUpdate(data) {
        console.log("Got status: ", data);
    }

    openGallery() {
        this.gallery.openGallery();
    }

    update(newItems, append = false) {
        let updatedDynamicElements = [];
        if (append) {
            updatedDynamicElements = [...self.currentElements, ...newItems];
        } else {
            updatedDynamicElements = newItems;
        }

        if (updatedDynamicElements.length > 0) {
            this.currentElements = updatedDynamicElements;
            let dynamicElements = this.currentElements.map((element) => ({
                src: element.path,
                thumb: element.path,
                subHtml: `<div class="lightGallery-captions">
          <h4>${element.caption}</h4>
          <p>${element.description}</p>
        </div>`,
            }));
            this.gallery.refresh(dynamicElements);
        }
    }
}

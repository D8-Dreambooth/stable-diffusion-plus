class InlineGallery {
    constructor(containerId, options = {}, dynamicElements = []) {
        this.container = document.getElementById(containerId);
        this.currentElements = dynamicElements;
        this.options = Object.assign({
            container: this.container,
            dynamic: true,
            hash: false,
            closable: false,
            thumbnail: true,
            showMaximizeIcon: true,
            plugins: [lgZoom, lgThumbnail, lgFullscreen],
            appendSubHtmlTo: '.lg-item',
            slideDelay: 400,
            dynamicEl: [],
        }, options);

        if (dynamicElements.length > 0) {
            this.options.dynamicEl = dynamicElements.map((element) => ({
                src: element.path,
                thumb: element.path,
                subHtml: `<div class="lightGallery-captions">
          <h4>${element.caption}</h4>
          <p>${element.description}</p>
        </div>`,
            }));
        }

        this.gallery = lightGallery(this.container, this.options);
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
            let dynamicElements = upatedDynamicElements.map((element) => ({
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

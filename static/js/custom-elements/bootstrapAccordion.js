class Accordion {
    /**
     * Creates an accordion instance for the given container element. You can specify data-accordion-param on the HTML element to set options.
     * @param {HTMLElement} container - The container element to turn into an accordion.
     * @param {Object} [options] - An optional dictionary of options to customize the accordion.
     * @param {string} [options.id=''] - The ID to use for the accordion body element. If not provided, a random ID will be generated.
     * @param {string} [options.labelID=''] - The ID to use for the accordion label element. If not provided, it will be set to the ID of the body element appended with "Label".
     * @param {string} [options.label=''] - The text content to use for the accordion label button.
     * @param {boolean} [options.collapsed=true] - Whether the accordion should start collapsed or expanded.
     */
    constructor(container, options = {}) {
        // Set default options
        const defaultOptions = {
            id: '',
            labelID: '',
            label: '',
            collapsed: true,
        };
        const mergedOptions = {...defaultOptions, ...options};

        // Generate random IDs for label and body if not provided in options
        const generateRandomID = () => Math.random().toString(36).substring(2, 15);
        if (!mergedOptions.id) {
            mergedOptions.id = generateRandomID() + 'Body';
        }
        if (!mergedOptions.labelID) {
            mergedOptions.labelID = mergedOptions.id + 'Label';
        }

        // Merge options with data attributes of container
        Object.keys(mergedOptions).forEach((optionKey) => {
            const dataAttribute = container.dataset[`accordion${optionKey}`];
            if (dataAttribute !== undefined) {
                mergedOptions[optionKey] = dataAttribute;
            }
        });

        // Store instance variables
        this.container = container;
        this.options = mergedOptions;

        // Set up accordion elements
        const header = container.querySelector('.accordion-button');
        header.textContent = this.options.label;
        header.setAttribute('aria-controls', this.options.id);
        header.setAttribute('id', this.options.labelID);
        const collapse = container.querySelector('.accordion-collapse');
        collapse.setAttribute('id', this.options.id);
        collapse.classList.toggle('show', !this.options.collapsed);

        // Bind methods to instance
        this.appendChild = this.appendChild.bind(this);
        this.deleteChild = this.deleteChild.bind(this);
    }

    /**
     * Appends a new child element to the accordion body.
     * @param {HTMLElement} child - The element to append to the accordion body.
     */
    appendChild(child) {
        const body = this.container.querySelector('.accordion-body');
        body.appendChild(child);
    }

    /**
     * Deletes a child element from the accordion body.
     * @param {HTMLElement} child - The element to delete from the accordion body.
     */
    deleteChild(child) {
        const body = this.container.querySelector('.accordion-body');
        body.removeChild(child);
    }
}

// Add jQuery plugin
$.fn.Accordion = function (selector = '.bootstrapAccordion', options) {
    return this.filter(selector).each(function () {
        new Accordion(this, options);
    });
};

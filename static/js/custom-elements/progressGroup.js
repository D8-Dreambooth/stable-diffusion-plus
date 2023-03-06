class ProgressGroup {
    constructor(parentElement, options) {
        this.parentElement = parentElement;
        this.update = this.update.bind(this);

        registerSocketMethod("progressGroup", "status", this.update);
      // Set options last with update(options)
        this.options = {
          progress_1_current: 0,
          progress_2_current: 0,
          progress_1_total: 0,
          progress_2_total: 0,
          progress_1_css: " bg-success",
          progress_2_css: " bg-warning",
          status: "",
          status2: "",
          show_bar1: true,
          show_bar2: true,
          show_primary_status: true,
          show_secondary_status: true,
          show_percent: true
        };


        // Create HTML elements
        this.progressContainer = document.createElement("div");
        this.progressContainer.classList.add("progressContainer");

        const progressRow = document.createElement("div");
        progressRow.classList.add("progressRow");

        this.progressBar1 = document.createElement("div");
        this.progressBar1.classList.add("progress-bar");
        this.progressBar2 = document.createElement("div");
        this.progressBar2.classList.add("progress-bar");

        const progressGroup = document.createElement("div");
        progressGroup.classList.add("progress");
        progressGroup.appendChild(this.progressBar1);
        progressGroup.appendChild(this.progressBar2);
        progressRow.appendChild(progressGroup);

        const statusRowPrimary = document.createElement("div");
        statusRowPrimary.classList.add("row", "statusRowPrimary");

        const primary_status = document.createElement("div");
        primary_status.classList.add("status_primary");
        primary_status.innerHTML = "";
        this.primary_status = primary_status;
        statusRowPrimary.appendChild(primary_status);

        const statusRowSecondary = document.createElement("div");
        statusRowSecondary.classList.add("row", "statusRowSecondary");

        const secondary_status = document.createElement("div");
        secondary_status.classList.add("status_secondary");
        secondary_status.innerHTML = "";
        this.secondary_status = secondary_status;
        statusRowSecondary.appendChild(secondary_status);

        this.progressContainer.appendChild(progressRow);
        this.progressContainer.appendChild(statusRowPrimary);
        this.progressContainer.appendChild(statusRowSecondary);

        // Append to parent element
        this.parentElement.appendChild(this.progressContainer);

        // Update the component with the options
        this.update(options);
    }

    update(options) {
        if (options.hasOwnProperty("status")) {
            options = options.status;
        }
        // Merge user options with default options
        this.options = {...this.options, ...options};
        console.log("Updated options: ", this.options, this.progressBar1);
        // Update progress bars
        this.progressBar1.setAttribute("aria-valuenow", this.options.progress_1_current);
        this.progressBar1.style.setProperty("width", this.options.progress_1_current + "%");

        this.progressBar2.setAttribute("aria-valuenow", this.options.progress_2_current);
        this.progressBar2.style.setProperty("width", this.options.progress_2_current + "%");

        // Update progress bar visibility
        if (this.options.show_bar1) {
            this.progressBar1.style.setProperty("display", "block");
        } else {
            this.progressBar1.style.setProperty("display", "none");
        }

        if (this.options.show_bar2) {
            this.progressBar2.style.setProperty("display", "block");
        } else {
            this.progressBar2.style.setProperty("display", "none");
        }

        if (this.options.show_percent) {
            let pct_1 = (this.options.progress_1_current / this.options.progress_1_total) * 100;
            let pct_2 = (this.options.progress_2_current / this.options.progress_2_total) * 100;
            this.progressBar1.innerHTML = String(pct_1) + "%";
            this.progressBar2.innerHTML = String(pct_2) + "%";
        } else {
            this.progressBar1.innerHTML = "";
            this.progressBar2.innerHTML = "";
        }

        // Update status text
        this.primary_status.innerHTML = this.options.status;
        this.secondary_status.innerHTML = this.options.status2;

        // Update status text visibility
        if (this.options.show_primary_status) {
            this.primary_status.style.setProperty("display", "block");
        } else {
            this.primary_status.style.setProperty("display", "none");
        }

        if (this.options.show_secondary_status) {
            this.secondary_status.style.setProperty("display", "block");
        } else {
            this.secondary_status.style.setProperty("display", "none");
        }

        // Update progress bar CSS classes
        this.progressBar1.className = "progress-bar" + this.options.progress_1_css;
        this.progressBar2.className = "progress-bar" + this.options.progress_2_css;
    }


}
     

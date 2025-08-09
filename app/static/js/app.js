class InventoryApp {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.setupFormValidation();
        this.setupTooltips();
        this.setupAutoSave();
        this.setupHardwareFormFeatures();
        this.setupStatusFormFeatures();
        this.setupDashboardFeatures();
    }

    setupEventListeners() {
        document.body.addEventListener('htmx:beforeRequest', this.handleBeforeRequest.bind(this));
        document.body.addEventListener('htmx:afterRequest', this.handleAfterRequest.bind(this));
        document.body.addEventListener('htmx:responseError', this.handleResponseError.bind(this));
        document.body.addEventListener('htmx:sendError', this.handleSendError.bind(this));
        document.body.addEventListener('htmx:beforeSwap', this.handleBeforeSwap.bind(this));


        document.addEventListener('submit', this.handleFormSubmit.bind(this), true);


        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-copy]')) {
                this.copyToClipboard(e.target.dataset.copy);
            }
        });


        const searchInputs = document.querySelectorAll('input[type="search"], input[name="search"]');
        searchInputs.forEach(input => {
            input.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
        });
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {

            if ((e.ctrlKey || e.metaKey)) {
                switch (e.key) {
                    case 'k':
                        e.preventDefault();
                        this.focusSearch();
                        break;
                    case 'n':
                        e.preventDefault();
                        this.navigateToAddForm();
                        break;
                    case 'r':
                        e.preventDefault();
                        this.refreshData();
                        break;
                    case 's':

                        if (document.querySelector('form[data-hardware-form]')) {
                            e.preventDefault();
                            this.submitHardwareForm();
                        }
                        break;
                }
            }


            if (e.key === 'Escape') {
                this.handleEscapeKey(e);
            }


            if (e.altKey) {
                switch (e.key) {
                    case 'd':
                        e.preventDefault();
                        window.location.href = '/';
                        break;
                    case 'h':
                        e.preventDefault();
                        window.location.href = '/hardware';
                        break;
                }
            }
        });
    }

    setupFormValidation() {

        const forms = document.querySelectorAll('form[novalidate]');
        forms.forEach(form => {
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', () => this.validateField(input));
                input.addEventListener('input', () => this.clearFieldError(input));
            });
        });
    }

    setupTooltips() {

        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }

    setupAutoSave() {

        const forms = document.querySelectorAll('form[data-autosave]');
        forms.forEach(form => {
            const formId = form.id || 'autosave-form';


            this.loadFormData(form, formId);


            form.addEventListener('input', this.debounce(() => {
                this.saveFormData(form, formId);
            }, 1000));
        });
    }

    setupHardwareFormFeatures() {

        const hardwareForm = document.querySelector('form[data-hardware-form]');
        if (!hardwareForm) return;


        const firstInput = hardwareForm.querySelector('#hostname');
        if (firstInput) firstInput.focus();


        const macInput = hardwareForm.querySelector('#mac');
        if (macInput) {
            macInput.addEventListener('input', this.handleMacAddressFormatting.bind(this));
        }


        const ipInput = hardwareForm.querySelector('#ip');
        if (ipInput) {
            ipInput.addEventListener('blur', this.handleIpValidation.bind(this));
        }
    }

    setupStatusFormFeatures() {

        const statusSelect = document.querySelector('#new-status');
        if (!statusSelect) return;


        statusSelect.focus();


        statusSelect.addEventListener('change', this.handleStatusPreview.bind(this));
    }

    setupDashboardFeatures() {

    }


    handleBeforeRequest(event) {

        const target = event.detail.target;
        if (target) {
            target.classList.add('htmx-loading');
        }


        if (event.detail.elt.tagName === 'FORM') {
            const submitButtons = event.detail.elt.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(btn => {
                btn.disabled = true;
                btn.dataset.originalText = btn.innerHTML;
                btn.innerHTML = '<span class="loading-spinner me-1"></span>Processing...';
            });
        }
    }

    handleAfterRequest(event) {

        const target = event.detail.target;
        if (target) {
            target.classList.remove('htmx-loading');
        }


        if (event.detail.elt.tagName === 'FORM') {
            const submitButtons = event.detail.elt.querySelectorAll('button[type="submit"]');
            submitButtons.forEach(btn => {
                btn.disabled = false;
                if (btn.dataset.originalText) {
                    btn.innerHTML = btn.dataset.originalText;
                    delete btn.dataset.originalText;
                }
            });
        }


        if (event.detail.successful) {
            this.handleSuccessResponse(event);
        }


        this.reinitializeComponents();
    }

    handleBeforeSwap(event) {

        if (!event.detail.target || event.detail.target.closest('nav')) {
            event.preventDefault();
            return;
        }


        if (event.detail.xhr.status === 422) {
            event.detail.shouldSwap = false;
            event.detail.isError = false;
            this.showAlert('warning', 'Please correct the errors in the form.');
        }
    }

    handleResponseError(event) {
        console.error('HTMX Response Error:', event.detail);
        this.showAlert('danger', 'Server error occurred. Please try again.');
    }

    handleSendError(event) {
        console.error('HTMX Send Error:', event.detail);
        this.showAlert('danger', 'Network error. Please check your connection.');
    }

    handleFormSubmit(event) {
        const form = event.target;


        if (!form.checkValidity()) {
            event.preventDefault();
            form.classList.add('was-validated');

            const inputs = form.querySelectorAll('input, select, textarea');
            let firstInvalid = null;
            inputs.forEach((input) => {
                if (!input.checkValidity()) {
                    this.validateField(input);
                    if (!firstInvalid) firstInvalid = input;
                }
            });
            if (firstInvalid) {
                try { firstInvalid.focus({ preventScroll: false }); } catch (e) { /* ignore */ }
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            this.showAlert('warning', 'Please correct the errors in the form.');
            return;
        }


        if (form.dataset.autosave) {
            const formId = form.id || 'autosave-form';
            localStorage.removeItem(`form-data-${formId}`);
        }
    }

    handleSuccessResponse(event) {

        const shouldShowAlert = (
            (event.detail.elt.tagName === 'FORM' &&
                (event.detail.elt.method === 'POST' || event.detail.elt.method === 'PUT' || event.detail.elt.method === 'DELETE')) ||
            event.detail.elt.hasAttribute('data-success-message')
        );

        if (shouldShowAlert && event.detail.xhr.status === 200) {
            this.showAlert('success', 'Operation completed successfully!');
        }


        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }

    handleSearch(event) {
        const searchTerm = event.target.value;
        const form = event.target.closest('form');

        if (form && searchTerm.length >= 2) {
            htmx.trigger(form, 'search');
        } else if (searchTerm.length === 0) {
            htmx.trigger(form, 'search');
        }
    }

    handleEscapeKey(event) {

        const searchInput = document.querySelector('input[name="search"]:focus');
        if (searchInput) {
            searchInput.value = '';
            htmx.trigger(searchInput.closest('form'), 'search');
            return;
        }


        if (document.querySelector('form[data-hardware-form]')) {
            if (confirm('Are you sure you want to cancel? Any unsaved changes will be lost.')) {
                window.location.href = '/hardware';
            }
            return;
        }


        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }

    handleMacAddressFormatting(event) {
        let value = event.target.value.replace(/[^a-fA-F0-9]/g, '');
        if (value.length > 12) value = value.slice(0, 12);

        let formatted = value.match(/.{1,2}/g)?.join(':') || value;
        if (formatted !== event.target.value) {
            event.target.value = formatted;
        }
    }

    handleIpValidation(event) {
        const ipPattern = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        if (event.target.value && !ipPattern.test(event.target.value)) {
            event.target.classList.add('is-invalid');
        } else {
            event.target.classList.remove('is-invalid');
        }
    }

    handleStatusPreview(event) {
        const selectedStatus = event.target.value;
        const statusMap = {
            'IN_STOCK': { text: 'In Stock', class: 'status-in-stock' },
            'RESERVED': { text: 'Reserved', class: 'status-reserved' },
            'IMAGING': { text: 'Imaging', class: 'status-imaging' },
            'SHIPPED': { text: 'Shipped', class: 'status-shipped' },
            'COMPLETED': { text: 'Completed', class: 'status-completed' }
        };


        const existingPreview = document.querySelector('.status-preview');
        if (existingPreview) existingPreview.remove();

        if (selectedStatus && statusMap[selectedStatus]) {
            const preview = document.createElement('div');
            preview.className = `status-preview mt-2 small text-muted`;
            preview.innerHTML = `Preview: <span class="status-pill ${statusMap[selectedStatus].class}"><span class="status-badge ${statusMap[selectedStatus].class}"></span>${statusMap[selectedStatus].text}</span>`;
            event.target.parentNode.appendChild(preview);
        }
    }


    focusSearch() {
        const searchInput = document.querySelector('input[name="search"], #search');
        if (searchInput) {
            searchInput.focus();
            searchInput.select();
        }
    }

    navigateToAddForm() {
        window.location.href = '/hardware/add';
    }

    refreshData() {
        const refreshButton = document.querySelector('[hx-get*="refresh"]');
        if (refreshButton) {
            htmx.trigger(refreshButton, 'click');
        } else {
            location.reload();
        }
    }

    submitHardwareForm() {
        const form = document.querySelector('form[data-hardware-form]');
        if (form) {
            form.dispatchEvent(new Event('submit'));
        }
    }

    validateField(field) {
        const isValid = field.checkValidity();

        if (!isValid) {
            field.classList.add('is-invalid');
            this.showFieldError(field, field.validationMessage);
        } else {
            field.classList.remove('is-invalid');
            field.classList.add('is-valid');
            this.clearFieldError(field);
        }

        return isValid;
    }

    clearFieldError(field) {
        field.classList.remove('is-invalid');
        const feedback = field.parentNode.querySelector('.invalid-feedback');
        if (feedback) {
            feedback.remove();
        }
    }

    showFieldError(field, message) {
        this.clearFieldError(field);

        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;

        field.parentNode.appendChild(feedback);
    }

    copyToClipboard(text) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                this.showAlert('success', 'Copied to clipboard!', 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                this.fallbackCopyTextToClipboard(text);
            });
        } else {
            this.fallbackCopyTextToClipboard(text);
        }
    }

    fallbackCopyTextToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            document.execCommand('copy');
            this.showAlert('success', 'Copied to clipboard!', 2000);
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
            this.showAlert('warning', 'Unable to copy to clipboard', 3000);
        }

        document.body.removeChild(textArea);
    }

    showAlert(type, message, duration = 5000) {
        if (window.showAlert && window.showAlert !== this.showAlert) {
            window.showAlert(type, message, duration);
            return;
        }

        const alertsContainer = document.getElementById('alerts-container') || document.body;
        const alertId = 'alert-' + Date.now();

        const iconMap = {
            'success': 'fas fa-check-circle',
            'danger': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-circle',
            'info': 'fas fa-info-circle'
        };

        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="${iconMap[type] || 'fas fa-info-circle'} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        alertsContainer.insertAdjacentHTML('beforeend', alertHtml);

        // Auto dismiss
        if (duration > 0) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            }, duration);
        }
    }

    saveFormData(form, formId) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData);
        localStorage.setItem(`form-data-${formId}`, JSON.stringify(data));
    }

    loadFormData(form, formId) {
        const savedData = localStorage.getItem(`form-data-${formId}`);
        if (savedData) {
            try {
                const data = JSON.parse(savedData);
                Object.keys(data).forEach(key => {
                    const field = form.querySelector(`[name="${key}"]`);
                    if (field) {
                        field.value = data[key];
                    }
                });
            } catch (err) {
                console.error('Error loading form data:', err);
            }
        }
    }

    reinitializeComponents() {
        // Reinitialize tooltips for new content
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]:not([data-bs-original-title])'));
        tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

        // Reinitialize any custom components
        this.initializeCustomSelects();
        this.initializeCounters();
        this.setupStatusFormFeatures();
    }

    initializeCustomSelects() {
        // Enhanced select dropdowns
        const selects = document.querySelectorAll('select.form-select:not(.initialized)');
        selects.forEach(select => {
            select.classList.add('initialized');

            // Add search functionality for large select lists
            if (select.options.length > 10) {
                this.addSelectSearch(select);
            }
        });
    }

    initializeCounters() {
        // Animated counters for statistics
        const counters = document.querySelectorAll('.stats-number:not(.counted)');
        counters.forEach(counter => {
            counter.classList.add('counted');
            const target = parseInt(counter.textContent);
            const duration = 1000;
            const increment = target / (duration / 16);
            let current = 0;

            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    counter.textContent = Math.floor(current);
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.textContent = target;
                }
            };

            // Start animation when element is in viewport
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        updateCounter();
                        observer.unobserve(entry.target);
                    }
                });
            });

            observer.observe(counter);
        });
    }

    addSelectSearch(select) {
        // This would add a search input above large select dropdowns
        // Implementation would depend on specific requirements
        console.log('Adding search to select:', select);
    }

    debounce(func, wait, immediate) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                timeout = null;
                if (!immediate) func.apply(this, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(this, args);
        };
    }
}

// Global utility functions
window.InventoryUtils = {
    formatDate: (dateString) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    formatMAC: (mac) => {
        return mac.replace(/[^a-fA-F0-9]/g, '')
            .match(/.{1,2}/g)
            ?.join(':') || mac;
    },

    validateIP: (ip) => {
        const ipPattern = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        return ipPattern.test(ip);
    },

    generateUUID: () => {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            const r = Math.random() * 16 | 0;
            const v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
};

// Global functions for template compatibility
window.copyToClipboard = function (text) {
    if (window.inventoryApp) {
        window.inventoryApp.copyToClipboard(text);
    }
};

window.deleteHardware = function (hardwareId, hostname) {
    if (confirm(`Are you sure you want to delete "${hostname}"? This action cannot be undone.`)) {
        htmx.ajax('DELETE', `/hardware/${hardwareId}`, {
            target: '#hardware-table-container',
            swap: 'outerHTML'
        });
    }
};

window.clearFilters = function () {
    const form = document.querySelector('form#hardware-filter-form') || document.querySelector('form[hx-get="/hardware"]');

    if (form) {
        ['search', 'center'].forEach((name) => {
            const el = form.querySelector(`[name="${name}"]`);
            if (el) el.value = '';
        });
        ['status', 'model'].forEach((name) => {
            const el = form.querySelector(`select[name="${name}"]`);
            if (el) el.value = '';
        });
    }

    if (window.history && window.history.pushState) {
        window.history.pushState({}, '', '/hardware');
    }

    const container = document.getElementById('hardware-table-container');
    if (container) {
        htmx.ajax('GET', '/hardware', { target: '#hardware-table-container', swap: 'innerHTML' });
    }
};

window.clearDashboardFilters = function () {
    const form = document.getElementById('dashboard-filter-form');
    if (!form) return;

    ['search', 'center'].forEach((name) => {
        const el = form.querySelector(`[name="${name}"]`);
        if (el) el.value = '';
    });

    ['status', 'model'].forEach((name) => {
        const el = form.querySelector(`select[name="${name}"]`);
        if (el) { el.selectedIndex = 0; el.value = ''; }
    });

    if (window.htmx) {
        htmx.trigger(form, 'submit');
    } else {
        window.location.href = '/hardware';
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.inventoryApp = new InventoryApp();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InventoryApp;
}

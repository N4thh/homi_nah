/**
 * Pagination Component JavaScript
 * Provides enhanced functionality for pagination components
 */

class PaginationManager {
  constructor(options = {}) {
    this.options = {
      baseUrl: options.baseUrl || "",
      baseParams: options.baseParams || {},
      anchor: options.anchor || "",
      loadingClass: "pagination-loading",
      ...options,
    };

    this.init();
  }

  init() {
    this.bindEvents();
    this.setupKeyboardNavigation();
  }

  bindEvents() {
    // Handle pagination link clicks
    document.addEventListener("click", (e) => {
      const paginationLink = e.target.closest(".pagination .page-link");
      if (paginationLink && !paginationLink.classList.contains("disabled")) {
        this.handlePaginationClick(e, paginationLink);
      }
    });

    // Handle jump to page form submission
    document.addEventListener("submit", (e) => {
      const jumpForm = e.target.closest('form[action*="page"]');
      if (jumpForm) {
        this.handleJumpToPage(e, jumpForm);
      }
    });

    // Handle number input changes
    document.addEventListener("change", (e) => {
      if (e.target.type === "number" && e.target.name === "page") {
        this.handlePageInputChange(e);
      }
    });
  }

  handlePaginationClick(e, link) {
    const href = link.getAttribute("href");
    if (href && href !== "#") {
      this.showLoading();
      // Let the browser handle the navigation
      // The loading state will be cleared when the page loads
    }
  }

  handleJumpToPage(e, form) {
    e.preventDefault();

    const formData = new FormData(form);
    const page = formData.get("page");
    const action = form.getAttribute("action");

    if (page && page > 0) {
      this.showLoading();

      // Build URL with page parameter
      const url = new URL(action, window.location.origin);
      url.searchParams.set("page", page);

      // Navigate to the new page
      window.location.href = url.toString();
    }
  }

  handlePageInputChange(e) {
    const page = parseInt(e.target.value);
    const maxPage = parseInt(e.target.getAttribute("max"));

    if (page < 1) {
      e.target.value = 1;
    } else if (page > maxPage) {
      e.target.value = maxPage;
    }
  }

  setupKeyboardNavigation() {
    document.addEventListener("keydown", (e) => {
      // Only handle keyboard navigation when pagination is focused
      const pagination = document.querySelector(".pagination:focus-within");
      if (!pagination) return;

      const activePage = pagination.querySelector(
        ".page-item.active .page-link"
      );
      if (!activePage) return;

      let targetLink = null;

      switch (e.key) {
        case "ArrowLeft":
          targetLink = pagination.querySelector(
            '.page-item:not(.disabled) .page-link[aria-label*="Trang trước"]'
          );
          break;
        case "ArrowRight":
          targetLink = pagination.querySelector(
            '.page-item:not(.disabled) .page-link[aria-label*="Trang sau"]'
          );
          break;
        case "Home":
          targetLink = pagination.querySelector(
            '.page-item:not(.disabled) .page-link[href*="page=1"]'
          );
          break;
        case "End":
          const lastPageLink = pagination.querySelector(
            '.page-item:not(.disabled) .page-link[href*="page="]:last-of-type'
          );
          if (lastPageLink && lastPageLink.textContent.match(/^\d+$/)) {
            targetLink = lastPageLink;
          }
          break;
      }

      if (targetLink) {
        e.preventDefault();
        targetLink.click();
      }
    });
  }

  showLoading() {
    const pagination = document.querySelector(".pagination");
    if (pagination) {
      pagination.classList.add(this.options.loadingClass);
    }
  }

  hideLoading() {
    const pagination = document.querySelector(".pagination");
    if (pagination) {
      pagination.classList.remove(this.options.loadingClass);
    }
  }

  // Utility method to create pagination URL
  createPaginationUrl(page, additionalParams = {}) {
    const params = { ...this.options.baseParams, ...additionalParams, page };
    const url = new URL(this.options.baseUrl, window.location.origin);

    Object.keys(params).forEach((key) => {
      if (
        params[key] !== null &&
        params[key] !== undefined &&
        params[key] !== ""
      ) {
        url.searchParams.set(key, params[key]);
      }
    });

    return url.toString() + this.options.anchor;
  }

  // Method to update pagination without page reload
  updatePagination(newData) {
    // This would be used for AJAX pagination
    // Implementation depends on specific requirements
    console.log("Update pagination with new data:", newData);
  }
}

/**
 * Pagination Utility Functions
 */
const PaginationUtils = {
  // Calculate pagination range
  calculateRange(currentPage, totalPages, range = 2) {
    const start = Math.max(1, currentPage - range);
    const end = Math.min(totalPages, currentPage + range);
    return { start, end };
  },

  // Format pagination info text
  formatInfo(currentPage, perPage, total) {
    const start = (currentPage - 1) * perPage + 1;
    const end = Math.min(currentPage * perPage, total);
    return `Hiển thị ${start} - ${end} trong ${total} kết quả`;
  },

  // Validate page number
  validatePage(page, totalPages) {
    return Math.max(1, Math.min(page, totalPages));
  },

  // Create pagination parameters for URL
  createParams(baseParams, page, additionalParams = {}) {
    return { ...baseParams, ...additionalParams, page };
  },
};

/**
 * Initialize pagination components
 */
function initializePagination() {
  // Initialize pagination manager
  window.paginationManager = new PaginationManager();

  // Add pagination info formatting
  document.querySelectorAll(".pagination-info").forEach((info) => {
    const currentPage = parseInt(info.dataset.currentPage) || 1;
    const perPage = parseInt(info.dataset.perPage) || 10;
    const total = parseInt(info.dataset.total) || 0;

    if (total > 0) {
      info.textContent = PaginationUtils.formatInfo(
        currentPage,
        perPage,
        total
      );
    }
  });

  // Add keyboard navigation hints
  document.querySelectorAll(".pagination").forEach((pagination) => {
    pagination.setAttribute("tabindex", "0");
    pagination.setAttribute("role", "navigation");
    pagination.setAttribute("aria-label", "Phân trang");
  });
}

/**
 * AJAX Pagination Support
 */
class AjaxPagination {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      url: options.url || "",
      method: options.method || "GET",
      params: options.params || {},
      onSuccess: options.onSuccess || null,
      onError: options.onError || null,
      ...options,
    };

    this.init();
  }

  init() {
    this.bindEvents();
  }

  bindEvents() {
    this.container.addEventListener("click", (e) => {
      const paginationLink = e.target.closest(".pagination .page-link");
      if (
        paginationLink &&
        paginationLink.href &&
        !paginationLink.classList.contains("disabled")
      ) {
        e.preventDefault();
        this.loadPage(paginationLink.href);
      }
    });
  }

  async loadPage(url) {
    try {
      this.showLoading();

      const response = await fetch(url, {
        method: this.options.method,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (this.options.onSuccess) {
        this.options.onSuccess(data);
      } else {
        this.updateContent(data);
      }
    } catch (error) {
      console.error("Pagination error:", error);
      if (this.options.onError) {
        this.options.onError(error);
      }
    } finally {
      this.hideLoading();
    }
  }

  updateContent(data) {
    // Update pagination content
    if (data.pagination) {
      this.container.innerHTML = data.pagination;
    }

    // Update table content
    if (data.content) {
      const tableBody = this.container.querySelector("tbody");
      if (tableBody) {
        tableBody.innerHTML = data.content;
      }
    }
  }

  showLoading() {
    this.container.classList.add("pagination-loading");
  }

  hideLoading() {
    this.container.classList.remove("pagination-loading");
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", initializePagination);

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = { PaginationManager, PaginationUtils, AjaxPagination };
}

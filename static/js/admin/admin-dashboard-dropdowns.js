/**
 * Admin Dashboard Dropdowns with Choices.js
 * Modern dropdown library implementation for chart period selectors
 */

// Chart dropdown instances storage
let chartDropdownInstances = {
  bookingChart: null,
  userChart: null,
  revenueChart: null,
};

// Filter & Sort dropdown instances storage
let filterSortDropdownInstances = {
  filterDropdown: null,
  sortDropdown: null,
};

// Helper: add multiple classes safely
function addClasses(el, classes) {
  if (!el || !classes) return;
  classes
    .split(/\s+/)
    .filter(Boolean)
    .forEach((c) => el.classList.add(c));
}

// Helper: decorate a Choices instance with extra classes (no spaces in classNames config!)
function decorateChoicesInstance(instance) {
  try {
    // Các phần tử bên trong Choices (v10+)
    const containerOuter = instance?.containerOuter?.element;
    const containerInner = instance?.containerInner?.element;
    const dropdown = instance?.dropdown?.element;

    addClasses(containerOuter, "chart-dropdown-choices");
    addClasses(containerInner, "chart-dropdown-inner");
    addClasses(dropdown, "chart-dropdown-list");

    // Debug: thêm style trực tiếp để đảm bảo không bị override
    if (containerOuter) {
      containerOuter.style.wordBreak = "keep-all";
      containerOuter.style.overflowWrap = "normal";
      containerOuter.style.whiteSpace = "nowrap";
    }

    if (dropdown) {
      dropdown.style.wordBreak = "keep-all";
      dropdown.style.overflowWrap = "normal";
      dropdown.style.whiteSpace = "nowrap";
    }

    // Áp dụng style cho tất cả items
    setTimeout(() => {
      if (
        instance &&
        instance.containerOuter &&
        instance.containerOuter.element
      ) {
        const items =
          instance.containerOuter.element.querySelectorAll(".choices__item");
        items.forEach((item) => {
          item.style.wordBreak = "keep-all";
          item.style.overflowWrap = "normal";
          item.style.whiteSpace = "nowrap";
          item.style.wordWrap = "normal";
        });
      }
    }, 100);
  } catch (_) {
    // ignore
  }
}

// Shared Choices.js config for all dropdowns
const choicesConfig = {
  searchEnabled: false,
  shouldSort: false,
  allowHTML: true,
  itemSelectText: "",
  classNames: {
    containerOuter: "choices",
    containerInner: "choices__inner",
    input: "choices__input",
    inputCloned: "choices__input--cloned",
    list: "choices__list",
    listItems: "choices__list--multiple",
    listSingle: "choices__list--single",
    listDropdown: "choices__list--dropdown",
    item: "choices__item",
    itemSelectable: "choices__item--selectable",
    itemDisabled: "choices__item--disabled",
    itemChoice: "choices__item--choice",
    placeholder: "choices__placeholder",
    group: "choices__group",
    groupHeading: "choices__heading",
    button: "choices__button",
  },
  callbackOnCreateTemplates: function (template) {
    return {
      item: ({ classNames }, data) => {
        return template(`
          <div class="${classNames.item} ${
          data.highlighted
            ? classNames.highlightedState
            : classNames.itemSelectable
        }" data-item data-id="${data.id}" data-value="${data.value}" ${
          data.active ? 'aria-selected="true"' : ""
        } ${data.disabled ? 'aria-disabled="true"' : ""}>
            <i class="fas fa-${data.customProperties?.icon || "circle"}"></i>
            ${data.label}
          </div>
        `);
      },
      choice: ({ classNames }, data) => {
        return template(`
          <div class="${classNames.item} ${classNames.itemChoice} ${
          data.disabled ? classNames.itemDisabled : classNames.itemSelectable
        }" data-select-text="${this.config.itemSelectText}" data-choice ${
          data.disabled
            ? 'data-choice-disabled aria-disabled="true"'
            : "data-choice-selectable"
        } data-id="${data.id}" data-value="${data.value}" ${
          data.groupId > 0 ? 'data-group-id="' + data.groupId + '"' : ""
        }>
            <i class="fas fa-${data.customProperties?.icon || "circle"}"></i>
            ${data.label}
          </div>
        `);
      },
    };
  },
};

/**
 * Initialize Choices.js dropdowns for chart period selectors
 */
function initializeChartDropdowns() {
  const localChoicesConfig = {
    searchEnabled: false,
    itemSelectText: "",
    shouldSort: false,
    // classNames: {} // bỏ hẳn để dùng mặc định của Choices
    callbackOnCreateTemplates: function (template) {
      return {
        item: ({ classNames }, data) => {
          return template(
            `<div class="${classNames.item} ${
              data.highlighted
                ? classNames.highlightedState
                : classNames.itemSelectable
            }" data-item data-id="${data.id}" data-value="${data.value}" ${
              data.active ? 'aria-selected="true"' : ""
            } ${data.disabled ? 'aria-disabled="true"' : ""}><i class="fas fa-${
              data.customProperties?.icon || "calendar"
            } me-2"></i>${data.label}</div>`
          );
        },
        choice: ({ classNames }, data) => {
          return template(
            `<div class="${classNames.item} ${classNames.itemChoice} ${
              data.disabled
                ? classNames.itemDisabled
                : classNames.itemSelectable
            }" data-select-text="${this.config.itemSelectText}" data-choice ${
              data.disabled
                ? 'data-choice-disabled aria-disabled="true"'
                : "data-choice-selectable"
            } data-id="${data.id}" data-value="${data.value}" ${
              data.groupId > 0 ? 'role="treeitem"' : 'role="option"'
            }><i class="fas fa-${
              data.customProperties?.icon || "calendar"
            } me-2"></i>${data.label}</div>`
          );
        },
      };
    },
  };

  // Initialize Booking Chart Period Dropdown
  const bookingSelect = document.getElementById("bookingChartPeriodSelect");
  if (bookingSelect && !chartDropdownInstances.bookingChart) {
    try {
      // Kiểm tra xem element đã được khởi tạo Choices chưa
      if (bookingSelect.classList.contains("choices__input")) {
        return;
      }

      const inst = new Choices(bookingSelect, {
        ...localChoicesConfig,
        placeholder: true,
        placeholderValue: "Chọn khoảng thời gian...",
      });
      chartDropdownInstances.bookingChart = inst;
      decorateChoicesInstance(inst);

      // Lắng nghe change an toàn (không phụ thuộc event.detail)
      bookingSelect.addEventListener("change", function (e) {
        const selectedValue = e.target.value;
        const selectedText =
          e.target.selectedOptions && e.target.selectedOptions[0]
            ? e.target.selectedOptions[0].text
            : "";

        if (window.updateBookingChart) {
          window.updateBookingChart(selectedValue);
        }
        const buttonText = document.getElementById("currentBookingPeriodText");
        if (buttonText) buttonText.textContent = selectedText;
      });
    } catch (error) {
      console.error("❌ Failed to initialize booking chart dropdown:", error);
    }
  }

  // Initialize User Growth Chart Period Dropdown
  const userSelect = document.getElementById("userChartPeriodSelect");
  if (userSelect && !chartDropdownInstances.userChart) {
    try {
      // Kiểm tra xem element đã được khởi tạo Choices chưa
      if (userSelect.classList.contains("choices__input")) {
        return;
      }

      const inst = new Choices(userSelect, {
        ...localChoicesConfig,
        placeholder: true,
        placeholderValue: "Chọn khoảng thời gian...",
      });
      chartDropdownInstances.userChart = inst;
      decorateChoicesInstance(inst);

      userSelect.addEventListener("change", function (e) {
        const selectedValue = e.target.value;
        const selectedText =
          e.target.selectedOptions && e.target.selectedOptions[0]
            ? e.target.selectedOptions[0].text
            : "";

        if (window.updateLineChart) {
          window.updateLineChart(selectedValue);
        }
        const buttonText = document.getElementById("currentPeriodText");
        if (buttonText) buttonText.textContent = selectedText;
      });
    } catch (error) {
      console.error("❌ Failed to initialize user chart dropdown:", error);
    }
  }

  // Initialize Revenue Chart Year Dropdown
  const revenueSelect = document.getElementById("revenueYearSelect");
  if (revenueSelect && !chartDropdownInstances.revenueChart) {
    try {
      // Kiểm tra xem element đã được khởi tạo Choices chưa
      if (revenueSelect.classList.contains("choices__input")) {
        return;
      }

      const inst = new Choices(revenueSelect, {
        ...localChoicesConfig,
        placeholder: true,
        placeholderValue: "Chọn năm...",
      });
      chartDropdownInstances.revenueChart = inst;
      decorateChoicesInstance(inst);

      revenueSelect.addEventListener("change", function (e) {
        const selectedValue = e.target.value;
        const selectedText =
          e.target.selectedOptions && e.target.selectedOptions[0]
            ? e.target.selectedOptions[0].text
            : "";

        if (window.updateRevenueChart) {
          window.updateRevenueChart(selectedValue);
        }
        const buttonText = document.getElementById("currentRevenueYearText");
        if (buttonText) buttonText.textContent = selectedText;
      });
    } catch (error) {
      console.error("❌ Failed to initialize revenue chart dropdown:", error);
    }
  }
}

/**
 * Destroy chart dropdown instances
 */
function destroyChartDropdowns() {
  Object.keys(chartDropdownInstances).forEach((key) => {
    if (chartDropdownInstances[key]) {
      try {
        chartDropdownInstances[key].destroy();
        chartDropdownInstances[key] = null;
      } catch (error) {
        console.error("❌ Failed to destroy " + key + " dropdown:", error);
      }
    }
  });
}

/**
 * Reinitialize dropdowns (useful for dynamic content)
 */
function reinitializeChartDropdowns() {
  destroyChartDropdowns();
  setTimeout(() => {
    initializeChartDropdowns();
  }, 100);
}

/**
 * Set dropdown value programmatically
 */
function setDropdownValue(dropdownType, value) {
  const instance = chartDropdownInstances[dropdownType];
  if (instance) {
    try {
      instance.setChoiceByValue(value);
    } catch (error) {
      console.error(
        "❌ Failed to set " + dropdownType + " dropdown value:",
        error
      );
    }
  }
}

/**
 * Get current dropdown value
 */
function getDropdownValue(dropdownType) {
  const instance = chartDropdownInstances[dropdownType];
  if (instance) {
    return instance.getValue(true);
  }
  return null;
}

// Export functions for global access
window.initializeChartDropdowns = initializeChartDropdowns;
window.destroyChartDropdowns = destroyChartDropdowns;
window.reinitializeChartDropdowns = reinitializeChartDropdowns;
window.setDropdownValue = setDropdownValue;
window.getDropdownValue = getDropdownValue;

// Auto-initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  const statsSection = document.getElementById("section-stats");
  if (statsSection) {
    const observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (
          mutation.type === "attributes" &&
          (mutation.attributeName === "class" ||
            mutation.attributeName === "style")
        ) {
          const isVisible =
            statsSection.classList.contains("active") ||
            (statsSection.style.display !== "none" &&
              getComputedStyle(statsSection).display !== "none");

          if (isVisible && !chartDropdownInstances.bookingChart) {
            setTimeout(() => {
              initializeChartDropdowns();
            }, 500);
          }
        }
      });
    });

    observer.observe(statsSection, { attributes: true });

    const isVisible =
      statsSection.classList.contains("active") ||
      (statsSection.style.display !== "none" &&
        getComputedStyle(statsSection).display !== "none");

    if (isVisible) {
      setTimeout(() => {
        initializeChartDropdowns();
      }, 1000);
    }
  }
});

/**
 * Initialize Filter & Sort Dropdowns with Choices.js
 */
function initializeFilterSortDropdowns() {
  console.log("🎯 Initializing filter & sort dropdowns...");

  // Simple Choices.js configuration for clean look like backup
  const filterConfig = {
    searchEnabled: false,
    shouldSort: false,
    allowHTML: false,
    itemSelectText: "",
    placeholder: true,
  };

  // Initialize Filter Dropdown (with Choices.js like chart dropdowns)
  const filterSelect = document.getElementById("filterSelect");
  if (filterSelect && !filterSortDropdownInstances.filterDropdown) {
    try {
      // Kiểm tra xem element đã được khởi tạo Choices chưa
      if (filterSelect.classList.contains("choices__input")) {
        return;
      }

      const inst = new Choices(filterSelect, {
        ...choicesConfig,
        placeholder: true,
        placeholderValue: "Chọn loại tài khoản...",
      });
      filterSortDropdownInstances.filterDropdown = inst;
      decorateChoicesInstance(inst);

      // Handle filter change (giống như chart dropdowns)
      filterSelect.addEventListener("change", function (event) {
        const selectedValue = event.target.value;
        console.log("🎯 Filter changed:", selectedValue);

        // Get current URL parameters
        const url = new URL(window.location.href);
        url.searchParams.set("role", selectedValue);
        url.hash = "#owner";

        // Navigate to new URL
        window.location.href = url.toString();
      });

      console.log("✅ Filter dropdown initialized with Choices.js");
    } catch (error) {
      console.error("❌ Failed to initialize filter dropdown:", error);
    }
  }

  // Initialize Sort Dropdown (with Choices.js like chart dropdowns)
  const sortSelect = document.getElementById("sortSelect");
  if (sortSelect && !filterSortDropdownInstances.sortDropdown) {
    try {
      // Kiểm tra xem element đã được khởi tạo Choices chưa
      if (sortSelect.classList.contains("choices__input")) {
        return;
      }

      const inst = new Choices(sortSelect, {
        ...choicesConfig,
        placeholder: true,
        placeholderValue: "Chọn cách sắp xếp...",
      });
      filterSortDropdownInstances.sortDropdown = inst;
      decorateChoicesInstance(inst);

      // Handle sort change (giống như chart dropdowns)
      sortSelect.addEventListener("change", function (event) {
        const selectedValue = event.target.value;
        console.log("📊 Sort changed:", selectedValue);

        // Get current URL parameters
        const url = new URL(window.location.href);
        if (selectedValue) {
          url.searchParams.set("sort", selectedValue);
        } else {
          url.searchParams.delete("sort");
        }
        url.hash = "#owner";

        // Navigate to new URL
        window.location.href = url.toString();
      });

      console.log("✅ Sort dropdown initialized with Choices.js");
    } catch (error) {
      console.error("❌ Failed to initialize sort dropdown:", error);
    }
  }
}

// Initialize filter/sort dropdowns when customer management section is shown
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(() => {
    initializeFilterSortDropdowns();
  }, 500);
});

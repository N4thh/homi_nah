/**
 * Admin Dashboard Core JavaScript
 * Handles: CSRF, Bootstrap initialization, Navigation, Section management
 */

// Global variables
let csrfToken = "";

/**
 * Initialize CSRF Token
 */
function initializeCSRF() {
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  if (csrfMeta) {
    csrfToken = csrfMeta.getAttribute("content");
  }
}

/**
 * Initialize Modal Z-Index Fix
 */
function initializeModalFixes() {
  // Handle modal z-index issues
  document.addEventListener("show.bs.modal", function (event) {
    const modal = event.target;
    const modalId = modal.id;

    // Force modal and backdrop to highest z-index
    setTimeout(() => {
      modal.style.zIndex = "1080";

      const backdrop = document.querySelector(".modal-backdrop");
      if (backdrop) {
        backdrop.style.zIndex = "1065";
        backdrop.style.backgroundColor = "rgba(0, 0, 0, 0.8)";
      }

      // Force navbar and sidebar behind modal
      const navbars = document.querySelectorAll(
        ".navbar, nav.navbar, .navbar-expand-lg, .navbar-dark"
      );
      const sidebars = document.querySelectorAll(
        ".sidebar, .admin-sidebar, .dashboard-sidebar"
      );

      // Force all navbar elements behind modal
      navbars.forEach((navbar) => {
        if (navbar) {
          navbar.style.zIndex = "1040";
          // Also force all child elements
          const navChildren = navbar.querySelectorAll("*");
          navChildren.forEach((child) => {
            child.style.zIndex = "1040";
          });
        }
      });

      // Force all sidebar elements behind modal
      sidebars.forEach((sidebar) => {
        if (sidebar) {
          sidebar.style.zIndex = "1040";
          // Also force all child elements
          const sidebarChildren = sidebar.querySelectorAll("*");
          sidebarChildren.forEach((child) => {
            child.style.zIndex = "1040";
          });
        }
      });

      console.log(`Modal ${modalId} z-index fixed`);
    }, 10);
  });

  // Clean up on modal hide
  document.addEventListener("hidden.bs.modal", function (event) {
    const navbars = document.querySelectorAll(
      ".navbar, nav.navbar, .navbar-expand-lg, .navbar-dark"
    );
    const sidebars = document.querySelectorAll(
      ".sidebar, .admin-sidebar, .dashboard-sidebar"
    );

    // Restore original z-index for all navbar elements
    navbars.forEach((navbar) => {
      if (navbar) {
        navbar.style.zIndex = "";
        // Also restore all child elements
        const navChildren = navbar.querySelectorAll("*");
        navChildren.forEach((child) => {
          child.style.zIndex = "";
        });
      }
    });

    // Restore original z-index for all sidebar elements
    sidebars.forEach((sidebar) => {
      if (sidebar) {
        sidebar.style.zIndex = "";
        // Also restore all child elements
        const sidebarChildren = sidebar.querySelectorAll("*");
        sidebarChildren.forEach((child) => {
          child.style.zIndex = "";
        });
      }
    });
  });
}

/**
 * Initialize Bootstrap Dropdowns
 */
function initializeBootstrapDropdowns() {
  // Wait a bit for Bootstrap to be fully ready
  setTimeout(function () {
    if (typeof bootstrap === "undefined") {
      console.error("Bootstrap is not loaded!");
      return;
    }

    // Find and initialize ALL dropdown elements
    const allDropdownToggles = document.querySelectorAll(
      '[data-bs-toggle="dropdown"]'
    );

    allDropdownToggles.forEach(function (element, index) {
      try {
        // Dispose any existing instance first
        const existingInstance = bootstrap.Dropdown.getInstance(element);
        if (existingInstance) {
          existingInstance.dispose();
        }

        // Create new dropdown instance
        const dropdown = new bootstrap.Dropdown(element, {
          autoClose: true,
          boundary: "viewport",
        });

        // Add debugging event listeners
        element.addEventListener("show.bs.dropdown", function () {
          console.log(
            "🔽 Dropdown opening:",
            element.id || element.textContent.trim()
          );
        });

        element.addEventListener("shown.bs.dropdown", function () {
          console.log(
            "✅ Dropdown opened:",
            element.id || element.textContent.trim()
          );
        });

        element.addEventListener("hide.bs.dropdown", function () {
          console.log(
            "🔼 Dropdown closing:",
            element.id || element.textContent.trim()
          );
        });
      } catch (error) {
        console.error(
          "✗ Failed to initialize dropdown:",
          element.id || element.className,
          error
        );
      }
    });

    console.log("✅ All dropdowns initialized successfully");

    // Test dropdowns after initialization
    setTimeout(() => {
      testBootstrapDropdowns();
    }, 500);

    // Special handling for navbar dropdown
    const navbarDropdown = document.getElementById("navbarDropdown");
    if (navbarDropdown) {
      try {
        const existingNavbarInstance =
          bootstrap.Dropdown.getInstance(navbarDropdown);
        if (existingNavbarInstance) {
          existingNavbarInstance.dispose();
        }

        const navbarDropdownInstance = new bootstrap.Dropdown(navbarDropdown, {
          autoClose: true,
          boundary: "viewport",
          popperConfig: {
            strategy: "fixed",
            placement: "bottom-end",
          },
        });
      } catch (error) {
        console.error("✗ Failed to initialize navbar dropdown:", error);
      }
    }

    // Close dropdowns when clicking outside
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".dropdown")) {
        document
          .querySelectorAll(".dropdown-menu.show")
          .forEach(function (menu) {
            menu.classList.remove("show");
          });

        // Reset all aria-expanded attributes
        document
          .querySelectorAll(".dropdown-toggle")
          .forEach(function (toggle) {
            toggle.setAttribute("aria-expanded", "false");
          });
      }
    });

    // Ensure all dropdown links work properly
    document.querySelectorAll(".dropdown-menu a").forEach(function (link) {
      link.addEventListener("click", function (e) {
        // Don't prevent default for actual links (like logout)
        if (
          this.href &&
          this.href !== "#" &&
          this.href !== "javascript:void(0)"
        ) {
          return true;
        }
      });
    });
  }, 500);
}

/**
 * Section Management System
 */
function showSection(sectionId) {
  // Hide all sections using Bootstrap classes with force
  document
    .querySelectorAll(".admin-section, .dashboard-section")
    .forEach((section) => {
      section.classList.remove("active");
      section.classList.add("d-none");
      section.classList.remove("d-block");
      section.style.display = "none"; // Force hide with inline style
    });

  // Show target section
  const targetSection = document.getElementById(`section-${sectionId}`);

  if (targetSection) {
    targetSection.classList.add("active");
    targetSection.classList.remove("d-none");
    targetSection.classList.add("d-block");
    targetSection.style.display = "block"; // Force show with inline style

    // Initialize charts when statistics section is shown
    if (sectionId === "stats") {
      setTimeout(() => {
        if (typeof initializeLineChart === "function") initializeLineChart();
        if (typeof initializeBookingChart === "function")
          initializeBookingChart();
        if (typeof initializeRevenueChart === "function")
          initializeRevenueChart();
      }, 200);
    }
  }

  // Update page title based on section
  const sectionInfo = {
    stats: {
      title: "Thống kê",
      subtitle: "Thống kê tổng quan hệ thống",
    },
    owner: {
      title: "Quản lý khách hàng",
      subtitle: "Quản lý tài khoản chủ nhà và người thuê",
    },
    admin: {
      title: "Quản lý Admin",
      subtitle: "Quản lý tài khoản quản trị viên",
    },
    homestays: {
      title: "Quản lý Homestay",
      subtitle: "Quản lý danh sách homestay",
    },
    bookings: {
      title: "Quản lý đặt phòng",
      subtitle: "Theo dõi và quản lý đặt phòng",
    },
    payments: {
      title: "Quản lý thanh toán",
      subtitle: "Theo dõi giao dịch và thanh toán",
    },
    reports: {
      title: "Báo cáo",
      subtitle: "Phân tích dữ liệu chi tiết",
    },
    settings: {
      title: "Cài đặt",
      subtitle: "Cấu hình hệ thống",
    },
  };

  const mainPageTitle = document.getElementById("main-page-title");
  if (mainPageTitle && sectionInfo[sectionId]) {
    mainPageTitle.textContent = sectionInfo[sectionId].title;
  }
}

/**
 * Handle hash changes for navigation
 */
function handleHashChange() {
  const hash = window.location.hash.substring(1);
  if (hash) {
    showSection(hash);
    // Update sidebar active state
    if (window.setActiveMenuItem) {
      window.setActiveMenuItem(hash);
    }
  }
}

/**
 * Initialize Navigation System
 */
function initializeNavigation() {
  // Listen for sidebar menu clicks
  document.addEventListener("sidebarMenuClick", function (event) {
    const section = event.detail.section;
    showSection(section);

    // Update URL hash without page reload
    if (history.pushState) {
      history.pushState(null, null, `#${section}`);
    }
  });

  // Listen for hash changes
  window.addEventListener("hashchange", handleHashChange);

  // Handle initial load
  if (!window.location.hash) {
    // Default to stats section if no hash

    showSection("stats");
    if (window.setActiveMenuItem) {
      window.setActiveMenuItem("stats");
    }
  } else {
    handleHashChange();
  }

  // Ensure stats section is shown by default on page load
  setTimeout(() => {
    const currentHash = window.location.hash.substring(1);
    if (!currentHash) {
      showSection("stats");

      // Force initialize charts after a delay
      setTimeout(() => {
        if (typeof initializeLineChart === "function") initializeLineChart();
        if (typeof initializeBookingChart === "function")
          initializeBookingChart();
        if (typeof initializeRevenueChart === "function")
          initializeRevenueChart();
      }, 500);
    } else {
      showSection(currentHash);
      if (window.setActiveMenuItem) {
        window.setActiveMenuItem(currentHash);
      }
    }
  }, 100);
}

/**
 * Language-specific updates
 */
function initializeLanguage() {
  const lang = localStorage.getItem("language") || "vi";
  if (lang === "vi") {
    const advTitle = document.getElementById("advancedVisualizeTitle");
    if (advTitle) advTitle.textContent = "Phân tích dữ liệu nâng cao";
  }
}

/**
 * Show Add Owner Modal using SweetAlert2
 */
function showAddOwnerModal() {
  Swal.fire({
    title: "Thêm tài khoản Owner mới",
    html: `
      <form id="addOwnerFormSwal" class="text-start">
        <div class="row mb-3">
          <div class="col-md-6">
            <label for="swal_first_name" class="form-label">Tên*</label>
            <input type="text" class="form-control" id="swal_first_name" name="first_name" required placeholder="Nhập tên" />
          </div>
          <div class="col-md-6">
            <label for="swal_last_name" class="form-label">Họ*</label>
            <input type="text" class="form-control" id="swal_last_name" name="last_name" required placeholder="Nhập họ" />
          </div>
        </div>
        <div class="mb-3">
          <label for="swal_username" class="form-label">Tên đăng nhập*</label>
          <input type="text" class="form-control" id="swal_username" name="username" required placeholder="Nhập tên đăng nhập" />
        </div>
        <div class="mb-3">
          <label for="swal_email" class="form-label">Email*</label>
          <input type="email" class="form-control" id="swal_email" name="email" required placeholder="Nhập email" />
        </div>
        <div class="mb-3">
          <label for="swal_phone" class="form-label">Số điện thoại*</label>
          <input type="tel" class="form-control" id="swal_phone" name="phone" required placeholder="Nhập số điện thoại" />
        </div>
        <div class="mb-3">
          <label for="swal_password" class="form-label">Mật khẩu*</label>
          <input type="password" class="form-control" id="swal_password" name="password" required placeholder="Nhập mật khẩu" />
          <div id="swalPasswordStrength" class="mt-2"></div>
        </div>
        <div class="mb-3">
          <label for="swal_confirm_password" class="form-label">Xác nhận mật khẩu*</label>
          <input type="password" class="form-control" id="swal_confirm_password" name="confirm_password" required placeholder="Nhập lại mật khẩu" />
          <div id="swalPasswordMatch" class="mt-2"></div>
        </div>
      </form>
    `,
    width: "600px",
    showCancelButton: true,
    confirmButtonText: '<i class="fas fa-plus me-2"></i>Thêm',
    cancelButtonText: "Hủy",
    confirmButtonColor: "#28a745",
    cancelButtonColor: "#6c757d",
    customClass: {
      popup: "swal-wide",
      confirmButton: "btn btn-success",
      cancelButton: "btn btn-secondary",
    },
    focusConfirm: false,
    preConfirm: () => {
      const form = document.getElementById("addOwnerFormSwal");
      const formData = new FormData(form);

      // Basic validation
      const firstName = formData.get("first_name");
      const lastName = formData.get("last_name");
      const username = formData.get("username");
      const email = formData.get("email");
      const phone = formData.get("phone");
      const password = formData.get("password");
      const confirmPassword = formData.get("confirm_password");

      // Validate required fields
      if (
        !firstName ||
        !lastName ||
        !username ||
        !email ||
        !phone ||
        !password ||
        !confirmPassword
      ) {
        Swal.showValidationMessage("Vui lòng điền đầy đủ thông tin");
        return false;
      }

      // Validate password match
      if (password !== confirmPassword) {
        Swal.showValidationMessage("Mật khẩu xác nhận không khớp");
        return false;
      }

      // Validate email format
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(email)) {
        Swal.showValidationMessage("Email không hợp lệ");
        return false;
      }

      // Validate phone format (Vietnamese phone numbers)
      const phoneRegex = /^(\+84|84|0)(3|5|7|8|9)([0-9]{8})$/;
      if (!phoneRegex.test(phone.replace(/\s+/g, ""))) {
        Swal.showValidationMessage("Số điện thoại không hợp lệ");
        return false;
      }

      // Validate password strength (minimum 6 characters)
      if (password.length < 6) {
        Swal.showValidationMessage("Mật khẩu phải có ít nhất 6 ký tự");
        return false;
      }

      return {
        first_name: firstName,
        last_name: lastName,
        username: username,
        email: email,
        phone: phone,
        password: password,
        confirm_password: confirmPassword,
      };
    },
  }).then((result) => {
    console.log("🎯 SweetAlert2 result:", result);
    if (result.isConfirmed) {
      console.log("✅ User confirmed, calling handleAddOwnerSubmission");
      // Handle form submission
      handleAddOwnerSubmission(result.value);
    } else {
      console.log("❌ User cancelled");
    }
  });
}

/**
 * Helper function to remove loading indicator
 */
function removeLoadingIndicator() {
  const loadingDiv = document.getElementById("simple-loading");
  if (loadingDiv) {
    loadingDiv.remove();
  }
}

/**
 * Handle Add Owner Form Submission using Admin API Service
 */
async function handleAddOwnerSubmission(formData) {
  console.log("🚀 handleAddOwnerSubmission started with data:", formData);

  try {
    console.log("🔍 Checking AdminAPI availability...");
    console.log("🔍 window.AdminAPI:", window.AdminAPI);
    console.log("🔍 typeof window.AdminAPI:", typeof window.AdminAPI);

    // Check if AdminAPI is available
    if (!window.AdminAPI) {
      console.error("❌ AdminAPI not available!");
      Swal.fire({
        icon: "error",
        title: "Lỗi!",
        text: "AdminAPI service not loaded. Please refresh the page.",
        confirmButtonColor: "#dc3545",
      });
      return;
    }

    console.log("✅ AdminAPI is available, proceeding...");

    // Show loading message (no modal to avoid conflicts)
    console.log("🔄 Starting API call...");

    // Show simple loading indicator
    const loadingDiv = document.createElement("div");
    loadingDiv.id = "simple-loading";
    loadingDiv.innerHTML = "🔄 Đang xử lý...";
    loadingDiv.style.cssText = `
      position: fixed;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(0,0,0,0.8);
      color: white;
      padding: 20px;
      border-radius: 10px;
      z-index: 9999;
      font-size: 16px;
    `;
    document.body.appendChild(loadingDiv);

    // Call API using service
    console.log("🌐 Calling AdminAPI.addOwner with data:", formData);
    const result = await window.AdminAPI.addOwner(formData);
    console.log("📥 API result:", result);

    // Remove loading indicator
    removeLoadingIndicator();
    console.log("✅ API call completed");

    if (result.success) {
      console.log("✅ API success, showing success alert...");
      // Show success alert and reload page
      Swal.fire({
        title: "Thành công!",
        text: result.data.message || "Đã thêm tài khoản Owner mới",
        icon: "success",
        confirmButtonText: "OK",
      });
      console.log("✅ Success alert shown");
      // Reload page
      setTimeout(() => location.reload(), 1000);
    } else {
      console.log("❌ API error, showing error alert...");
      // Show error alert
      Swal.fire({
        title: "Lỗi!",
        text:
          result.data.message ||
          result.data.error ||
          "Có lỗi xảy ra khi thêm tài khoản",
        icon: "error",
        confirmButtonText: "OK",
      });
      console.log("✅ Error alert shown");
    }
  } catch (error) {
    console.error("❌ Error in handleAddOwnerSubmission:", error);
    console.error("❌ Error type:", typeof error);
    console.error("❌ Error message:", error.message);
    console.error("❌ Error stack:", error.stack);

    // Remove loading indicator
    removeLoadingIndicator();
    console.log("❌ API call failed");

    Swal.fire({
      title: "Lỗi!",
      text: error.message || "Có lỗi xảy ra khi thêm tài khoản",
      icon: "error",
      confirmButtonText: "OK",
    });
  }
}

/**
 * Utility functions for admin operations using Admin API Service
 */
const AdminOperations = {
  // Toggle user status with confirmation
  async toggleUserStatus(userId, userName, userType = "user") {
    const result = await window.AdminAPI.showConfirmModal(
      `Thay đổi trạng thái ${userType}`,
      `Bạn có chắc muốn thay đổi trạng thái của ${userName}?`,
      "Xác nhận",
      "Hủy"
    );

    if (result.isConfirmed) {
      try {
        await window.AdminAPI.showLoadingModal();
        const response = await window.AdminAPI.toggleUserStatus(
          userId,
          userType
        );
        await window.AdminAPI.showSuccessModal(
          "Thành công!",
          `Đã thay đổi trạng thái ${userType}`,
          () => location.reload()
        );
      } catch (error) {
        await window.AdminAPI.showErrorModal(
          "Lỗi!",
          error.message || `Có lỗi khi thay đổi trạng thái ${userType}`
        );
      }
    }
  },

  // Delete user with confirmation
  async deleteUser(userId, userName, userType = "user") {
    const result = await window.AdminAPI.showConfirmModal(
      `Xóa ${userType}`,
      `Bạn có chắc muốn xóa ${userName}? Hành động này không thể hoàn tác.`,
      "Xóa",
      "Hủy"
    );

    if (result.isConfirmed) {
      try {
        await window.AdminAPI.showLoadingModal();
        await window.AdminAPI.deleteUser(userId, userType);
        await window.AdminAPI.showSuccessModal(
          "Đã xóa!",
          `${userType} đã được xóa thành công`,
          () => location.reload()
        );
      } catch (error) {
        await window.AdminAPI.showErrorModal(
          "Lỗi!",
          error.message || `Có lỗi khi xóa ${userType}`
        );
      }
    }
  },

  // Update commission
  async updateCommission(type, id, currentCommission, name) {
    const { value: newCommission } = await Swal.fire({
      title: `Cập nhật phí dịch vụ cho ${name}`,
      input: "number",
      inputLabel: "Phí dịch vụ (%)",
      inputValue: currentCommission,
      inputAttributes: {
        min: 0,
        max: 100,
        step: 0.1,
      },
      showCancelButton: true,
      confirmButtonText: "Cập nhật",
      cancelButtonText: "Hủy",
      inputValidator: (value) => {
        if (!value || value < 0 || value > 100) {
          return "Vui lòng nhập phí từ 0 đến 100%";
        }
      },
    });

    if (newCommission) {
      try {
        await window.AdminAPI.showLoadingModal();

        if (type === "owner") {
          await window.AdminAPI.updateOwnerCommission(
            id,
            parseFloat(newCommission)
          );
        } else if (type === "home") {
          await window.AdminAPI.updateHomeCommission(
            id,
            parseFloat(newCommission)
          );
        }

        await window.AdminAPI.showSuccessModal(
          "Thành công!",
          "Đã cập nhật phí dịch vụ",
          () => location.reload()
        );
      } catch (error) {
        await window.AdminAPI.showErrorModal(
          "Lỗi!",
          error.message || "Có lỗi khi cập nhật phí dịch vụ"
        );
      }
    }
  },
};

/**
 * Initialize Core Dashboard Functionality
 */
function initializeDashboardCore() {
  initializeCSRF();
  initializeModalFixes();
  initializeBootstrapDropdowns();
  initializeNavigation();
  initializeLanguage();

  // Replace Bootstrap modal with SweetAlert2
  const addOwnerButton = document.querySelector(
    '[data-bs-target="#addOwnerModal"]'
  );
  if (addOwnerButton) {
    addOwnerButton.removeAttribute("data-bs-toggle");
    addOwnerButton.removeAttribute("data-bs-target");
    addOwnerButton.addEventListener("click", function (e) {
      e.preventDefault();
      showAddOwnerModal();
    });
  }
}

// Export functions for global access
window.showSection = showSection;
window.handleHashChange = handleHashChange;
window.csrfToken = csrfToken;

/**
 * Test Bootstrap Dropdowns functionality (for remaining Bootstrap dropdowns)
 */
function testBootstrapDropdowns() {
  console.log("🧪 Testing remaining Bootstrap dropdowns...");

  // Only test dropdowns that are still using Bootstrap (not filter/sort anymore)
  const testDropdowns = [{ id: "navbarDropdown", name: "Navbar Dropdown" }];

  testDropdowns.forEach(({ id, name }) => {
    const element = document.getElementById(id);
    if (element) {
      const instance = bootstrap.Dropdown.getInstance(element);
      if (instance) {
        console.log(`✅ ${name} is properly initialized`);
      } else {
        console.error(`❌ ${name} instance not found`);
      }
    } else {
      console.log(`ℹ️ ${name} element not found (may not exist on this page)`);
    }
  });
}

// Auto-initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", initializeDashboardCore);

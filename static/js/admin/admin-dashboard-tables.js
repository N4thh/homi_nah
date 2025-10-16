/**
 * Admin Dashboard Tables JavaScript
 * Handles: Table actions, filtering, search, user management, dropdowns
 */

/**
 * Initialize Table Dropdowns
 * Let Bootstrap core handle dropdown creation, just add table-specific logic
 */
function initializeTableDropdowns() {
  // Don't create dropdowns here, let admin-dashboard-core.js handle that
  // Just add event listeners for dropdown items

  // Handle dropdown item clicks for actions
  document.addEventListener("click", function (e) {
    const dropdownItem = e.target.closest(".dropdown-item");
    if (dropdownItem && dropdownItem.closest("table")) {
      // Let the action handlers (like deleteUser, toggle-status) work normally
      // Don't prevent default here
    }
  });
}

/**
 * Initialize Filter System
 */
function initializeFilters() {
  const filterPills = document.querySelectorAll(".filter-pill");

  filterPills.forEach((pill) => {
    pill.addEventListener("click", function (e) {
      // Only handle if not a link with hash #owner
      const href = this.getAttribute("href");
      if (href && href.includes("#owner")) {
        // This is filter button in customer management, allow normal navigation
        return; // Don't prevent default, let link work normally
      }

      e.preventDefault();

      const status = this.getAttribute("data-status");

      // If clicking "All", just go to dashboard
      if (status === "all") {
        window.location.href = "/admin/dashboard";
        return;
      }

      // If clicking other filter, keep search query if exists
      const searchInput = document.querySelector('input[name="search"]');
      const searchQuery = searchInput ? searchInput.value.trim() : "";

      // Create new URL with parameters
      const url = new URL(window.location.origin + "/admin/dashboard");
      url.searchParams.set("status", status);
      if (searchQuery) {
        url.searchParams.set("search", searchQuery);
      }

      // Navigate to new URL
      window.location.href = url.toString();
    });
  });
}

/**
 * Initialize Search System
 */
function initializeSearch() {
  const searchForm = document.querySelector(".search-box form");
  if (searchForm) {
    searchForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const searchInput = this.querySelector('input[name="search"]');
      const searchTerm = searchInput ? searchInput.value.trim() : "";
      const currentFilter = document.querySelector(".filter-pill.active");
      const currentStatus = currentFilter
        ? currentFilter.getAttribute("data-status")
        : null;

      // Create new URL with parameters
      const url = new URL(window.origin + "/admin/dashboard");

      // Add search parameter if exists
      if (searchTerm) {
        url.searchParams.set("search", searchTerm);
      }

      // Add status parameter if filtering and not 'all'
      if (currentStatus && currentStatus !== "all") {
        url.searchParams.set("status", currentStatus);
      }

      // Navigate to new URL
      window.location.href = url.toString();
    });
  }
}

/**
 * User Action Handlers
 */
let userToDelete = null;

// User details view
window.viewUserDetails = function (element) {
  const userId = element.getAttribute("data-user-id");
  const userType = element.getAttribute("data-role-type");

  // TODO: Show user details modal or redirect to user detail page
  Swal.fire({
    title: "Thông tin người dùng",
    html: `<p><strong>ID:</strong> ${userId}</p><p><strong>Loại:</strong> ${userType}</p><p><em>Chức năng này đang được phát triển</em></p>`,
    icon: "info",
    confirmButtonText: "OK",
  });
};

// User deletion
window.deleteUser = function (element) {
  const userId = element.getAttribute("data-user-id");
  let userType = element.getAttribute("data-role-type");

  // Fallback: detect user type from role badge if data-role-type is missing
  if (!userType) {
    const userRow = element.closest("tr");
    const roleBadge = userRow.querySelector(".badge");
    if (roleBadge) {
      const roleText = roleBadge.textContent.trim().toLowerCase();
      if (roleText === "owner") userType = "owner";
      else if (roleText === "renter") userType = "renter";
      else if (roleText === "admin") userType = "admin";
    }
  }

  // Convert to lowercase if needed
  if (userType) {
    userType = userType.toLowerCase();
  }

  if (!userId || !userType) {
    console.error("Missing userId or userType:", { userId, userType });
    if (window.showToast) {
      window.showToast("error", "Không thể xác định thông tin người dùng");
    }
    return;
  }

  // Get user info from row
  const userRow = element.closest("tr");
  const username = userRow.querySelector("td:nth-child(3)").textContent.trim();
  const email = userRow.querySelector("td:nth-child(4)").textContent.trim();
  const phone = userRow.querySelector("td:nth-child(5)").textContent.trim();

  // Store info for confirmation
  userToDelete = {
    userId: userId,
    userType: userType,
  };

  // Display info in modal
  document.getElementById("delete-username-display").textContent = username;
  document.getElementById("delete-email-display").textContent = email;
  document.getElementById("delete-phone-display").textContent = phone;

  // Show confirmation modal
  const deleteConfirmModal = new bootstrap.Modal(
    document.getElementById("deleteConfirmModal")
  );
  deleteConfirmModal.show();
};

/**
 * Initialize User Management Modals
 */
function initializeUserManagement() {
  const deleteConfirmModal = new bootstrap.Modal(
    document.getElementById("deleteConfirmModal")
  );

  // Handle form submissions for delete
  document.querySelectorAll('form[action*="/delete"]').forEach((form) => {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      deleteForm = this;
      deleteConfirmModal.show();
    });
  });

  // Confirm delete button
  document
    .getElementById("confirmDeleteBtn")
    .addEventListener("click", function () {
      if (userToDelete) {
        // Disable button during request
        const btn = this;
        btn.disabled = true;
        btn.innerHTML =
          '<span class="spinner-border spinner-border-sm me-2"></span>Đang xóa...';

        // Use AdminAPI service
        window.AdminAPI.deleteUser(userToDelete.userId, userToDelete.userType)
          .then((result) => {
            if (result.success) {
              const message =
                result.data.message || "Xóa người dùng thành công";
              if (window.showToast) {
                window.showToast("success", message);
              }
              setTimeout(() => {
                location.reload();
              }, 1500);
            } else {
              const errorMessage = result.data.error || "Có lỗi xảy ra";
              if (window.showToast) {
                window.showToast("error", errorMessage);
              }
            }
            bootstrap.Modal.getInstance(
              document.getElementById("deleteConfirmModal")
            ).hide();
          })
          .catch((error) => {
            console.error("Delete user error:", error);
            if (window.showToast) {
              window.showToast("error", `Có lỗi xảy ra: ${error.message}`);
            }
            bootstrap.Modal.getInstance(
              document.getElementById("deleteConfirmModal")
            ).hide();
          })
          .finally(() => {
            // Re-enable button
            btn.disabled = false;
            btn.innerHTML = "Xác nhận xóa";
          });
      }
    });
}

/**
 * Initialize Toggle Status System
 */
function initializeToggleStatus() {
  const toggleStatusModal = new bootstrap.Modal(
    document.getElementById("toggleStatusModal")
  );
  const deactivateContent = document.getElementById("deactivateContent");
  const activateContent = document.getElementById("activateContent");
  const previousReason = document.getElementById("previousReason");
  const reasonTextarea = document.getElementById("reasonTextarea");
  const characterCount = document.querySelector(
    "#toggleStatusModal .character-count"
  );
  let currentForm = null;

  // Character count handler
  if (reasonTextarea) {
    reasonTextarea.addEventListener("input", function () {
      const currentLength = this.value.length;
      const maxLength = this.getAttribute("maxlength");
      if (characterCount) {
        characterCount.textContent = `${currentLength}/${maxLength} ký tự`;
      }
    });
  }

  // Toggle status button click handler
  const toggleButtons = document.querySelectorAll(
    'button[data-action="toggle-status"]'
  );

  toggleButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      const userId = this.getAttribute("data-user-id");
      const userType = this.getAttribute("data-role-type");
      const isActive = this.getAttribute("data-is-active") === "true";
      const username =
        this.getAttribute("data-username") || "Không có thông tin";
      const email = this.getAttribute("data-email") || "Không có thông tin";
      const phone = this.getAttribute("data-phone") || "Không có thông tin";

      // Store current button data for later use
      currentForm = {
        userId: userId,
        userType: userType,
        isActive: isActive,
        username: username,
        email: email,
        phone: phone,
      };

      // Reset form and update character count
      if (reasonTextarea) {
        reasonTextarea.value = "";
        if (characterCount) {
          characterCount.textContent = `0/${reasonTextarea.getAttribute(
            "maxlength"
          )} ký tự`;
        }
      }

      // Update user info in modal
      document.getElementById("toggle-username-display").textContent = username;
      document.getElementById("toggle-email-display").textContent = email;
      document.getElementById("toggle-phone-display").textContent = phone;

      document.getElementById("toggle-username-display-active").textContent =
        username;
      document.getElementById("toggle-email-display-active").textContent =
        email;
      document.getElementById("toggle-phone-display-active").textContent =
        phone;

      if (isActive) {
        // Show deactivation form
        deactivateContent.style.display = "block";
        activateContent.style.display = "none";
        if (reasonTextarea) {
          reasonTextarea.required = true;
        }
      } else {
        // Show activation form and get previous reason
        deactivateContent.style.display = "none";
        activateContent.style.display = "block";
        if (reasonTextarea) {
          reasonTextarea.required = false;
        }

        // Get previous deactivation reason
        fetch(`/admin/users/${userId}/reason?user_type=${userType}`)
          .then((response) => response.json())
          .then((data) => {
            if (previousReason) {
              previousReason.textContent = data.reason || "Không có lý do";
            }
          })
          .catch((error) => {
            console.error("Error:", error);
            if (previousReason) {
              previousReason.textContent = "Không thể lấy lý do";
            }
          });
      }
      toggleStatusModal.show();
    });
  });

  // Confirm toggle button click handler
  document
    .getElementById("confirmToggleBtn")
    .addEventListener("click", function () {
      if (currentForm) {
        const reason = reasonTextarea ? reasonTextarea.value : "";

        // Validation for deactivation (require reason)
        if (currentForm.isActive && (!reason || reason.trim() === "")) {
          Swal.fire({
            title: "Lỗi",
            text: "Vui lòng nhập lý do vô hiệu hóa tài khoản",
            icon: "error",
            confirmButtonText: "OK",
          });
          return;
        }

        // Use AdminAPI service
        window.AdminAPI.toggleUserStatus(
          currentForm.userId,
          currentForm.userType
        )
          .then((result) => {
            if (result.success) {
              const message =
                result.data.message || "Cập nhật trạng thái thành công";
              if (window.showToast) {
                window.showToast("success", message);
              }
              setTimeout(() => {
                location.reload();
              }, 1500);
            } else {
              const errorMessage = result.data.error || "Có lỗi xảy ra";
              if (window.showToast) {
                window.showToast("error", errorMessage);
              }
            }
            toggleStatusModal.hide();
          })
          .catch((error) => {
            console.error("Toggle status error:", error);
            if (window.showToast) {
              window.showToast("error", "Có lỗi xảy ra khi xử lý yêu cầu");
            }
            toggleStatusModal.hide();
          });
      }
    });
}

/**
 * Initialize Tables System
 */
function initializeTables() {
  initializeTableDropdowns();
  initializeFilters();
  initializeSearch();
  initializeUserManagement();
  initializeToggleStatus();
}

// Toggle user status function
window.toggleUserStatus = function (
  userId,
  userType,
  isActive,
  username,
  email,
  phone
) {
  console.log("🔄 toggleUserStatus called:", {
    userId,
    userType,
    isActive,
    username,
  });

  // Find the modal elements
  const toggleStatusModal = document.getElementById("toggleStatusModal");
  const deactivateContent = document.getElementById("deactivateContent");
  const activateContent = document.getElementById("activateContent");
  const previousReason = document.getElementById("previousReason");
  const reasonTextarea = document.getElementById("reasonTextarea");
  const characterCount = document.querySelector(
    "#toggleStatusModal .character-count"
  );

  if (!toggleStatusModal) {
    console.error("❌ Toggle status modal not found");
    return;
  }

  // Store current form data
  currentForm = {
    userId: userId,
    userType: userType,
    isActive: isActive,
    username: username,
    email: email,
    phone: phone,
  };

  // Show appropriate content
  if (isActive) {
    // Show deactivation content
    if (deactivateContent) deactivateContent.style.display = "block";
    if (activateContent) activateContent.style.display = "none";
    if (reasonTextarea) {
      reasonTextarea.required = true;
      reasonTextarea.style.display = "block";
    }
  } else {
    // Show activation content
    if (deactivateContent) deactivateContent.style.display = "none";
    if (activateContent) activateContent.style.display = "block";
    if (reasonTextarea) {
      reasonTextarea.required = false;
      reasonTextarea.style.display = "none";
    }
  }

  // Show modal
  const modal = new bootstrap.Modal(toggleStatusModal);
  modal.show();
};

// Export functions for global access
window.viewUserDetails = window.viewUserDetails;
window.deleteUser = window.deleteUser;

// Auto-initialize when DOM is loaded (with small delay to ensure dropdown handlers are ready)
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(initializeTables, 100);
});

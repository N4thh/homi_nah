/**
 * Admin API Service
 * Handles all admin-related API calls
 */
class AdminAPIService extends BaseAPIService {
  constructor() {
    super("/admin");
  }

  // ===============================
  // OWNER MANAGEMENT
  // ===============================

  /**
   * Add new owner
   * @param {Object} ownerData - Owner form data
   * @returns {Promise<Object>} API response
   */
  async addOwner(ownerData) {
    console.log("🏠 Adding new owner:", ownerData);
    return this.post("/add-owner", ownerData);
  }

  /**
   * Get owner details
   * @param {number} ownerId - Owner ID
   * @returns {Promise<Object>} API response
   */
  async getOwner(ownerId) {
    console.log(`🏠 Getting owner details: ${ownerId}`);
    return this.get(`/owners/${ownerId}`);
  }

  /**
   * Update owner
   * @param {number} ownerId - Owner ID
   * @param {Object} ownerData - Updated owner data
   * @returns {Promise<Object>} API response
   */
  async updateOwner(ownerId, ownerData) {
    console.log(`🏠 Updating owner ${ownerId}:`, ownerData);
    return this.put(`/owners/${ownerId}`, ownerData);
  }

  // ===============================
  // ADMIN MANAGEMENT
  // ===============================

  /**
   * Add new admin
   * @param {Object} adminData - Admin form data
   * @returns {Promise<Object>} API response
   */
  async addAdmin(adminData) {
    console.log("👑 Adding new admin:", adminData);
    return this.post("/add-admin", adminData);
  }

  /**
   * Get admin details
   * @param {number} adminId - Admin ID
   * @returns {Promise<Object>} API response
   */
  async getAdmin(adminId) {
    console.log(`👑 Getting admin details: ${adminId}`);
    return this.get(`/admins/${adminId}`);
  }

  /**
   * Update admin
   * @param {number} adminId - Admin ID
   * @param {Object} adminData - Updated admin data
   * @returns {Promise<Object>} API response
   */
  async updateAdmin(adminId, adminData) {
    console.log(`👑 Updating admin ${adminId}:`, adminData);
    return this.put(`/admins/${adminId}`, adminData);
  }

  // ===============================
  // USER MANAGEMENT (UNIFIED)
  // ===============================

  /**
   * Delete user (owner, renter, or admin)
   * @param {number} userId - User ID
   * @param {string} userType - User type ('owner', 'renter', 'admin')
   * @returns {Promise<Object>} API response
   */
  async deleteUser(userId, userType) {
    console.log(`🗑️ Deleting ${userType} user: ${userId}`);
    return this.delete(`/users/${userId}/delete`, { user_type: userType });
  }

  /**
   * Toggle user status (active/inactive)
   * @param {number} userId - User ID
   * @param {string} userType - User type ('owner', 'renter', 'admin')
   * @returns {Promise<Object>} API response
   */
  async toggleUserStatus(userId, userType) {
    console.log(`🔄 Toggling status for ${userType} user: ${userId}`);
    return this.post(`/users/${userId}/toggle-status`, { user_type: userType });
  }

  /**
   * Get users list with filters
   * @param {Object} filters - Filter parameters
   * @returns {Promise<Object>} API response
   */
  async getUsers(filters = {}) {
    console.log("👥 Getting users list with filters:", filters);
    const queryParams = new URLSearchParams(filters).toString();
    const endpoint = queryParams ? `/dashboard?${queryParams}` : "/dashboard";
    return this.get(endpoint);
  }

  // ===============================
  // DASHBOARD & STATISTICS
  // ===============================

  /**
   * Get dashboard statistics
   * @returns {Promise<Object>} API response
   */
  async getDashboardStats() {
    console.log("📊 Getting dashboard statistics");
    return this.get("/dashboard/stats");
  }

  /**
   * Get user growth data
   * @param {string} period - Time period ('week', 'month', 'year')
   * @returns {Promise<Object>} API response
   */
  async getUserGrowthData(period = "month") {
    console.log(`📈 Getting user growth data for: ${period}`);
    return this.get(`/dashboard/growth?period=${period}`);
  }

  // ===============================
  // COMMISSION MANAGEMENT
  // ===============================

  /**
   * Update owner commission
   * @param {number} ownerId - Owner ID
   * @param {number} commission - Commission percentage
   * @returns {Promise<Object>} API response
   */
  async updateOwnerCommission(ownerId, commission) {
    console.log(`💰 Updating owner ${ownerId} commission to: ${commission}%`);
    return this.post(`/api/owner/${ownerId}/commission`, { commission });
  }

  /**
   * Update home commission
   * @param {number} homeId - Home ID
   * @param {number} commission - Commission percentage
   * @returns {Promise<Object>} API response
   */
  async updateHomeCommission(homeId, commission) {
    console.log(`🏠 Updating home ${homeId} commission to: ${commission}%`);
    return this.post(`/api/home/${homeId}/commission`, { commission });
  }

  // ===============================
  // STATISTICS APIs
  // ===============================

  /**
   * Get owner revenue data
   * @returns {Promise<Object>} API response
   */
  async getOwnerRevenue() {
    console.log("💰 Getting owner revenue data");
    return this.get("/api/owner-revenue");
  }

  /**
   * Get user growth data for charts
   * @param {string} period - Time period
   * @returns {Promise<Object>} API response
   */
  async getUserGrowthData(period) {
    console.log(`📈 Getting user growth data for: ${period}`);
    return this.get(`/api/user-growth-data/${period}`);
  }

  /**
   * Get booking stats data
   * @param {string} period - Time period
   * @returns {Promise<Object>} API response
   */
  async getBookingStatsData(period) {
    console.log(`📊 Getting booking stats data for: ${period}`);
    return this.get(`/api/booking-stats-data/${period}`);
  }

  /**
   * Get revenue stats data
   * @param {number} year - Year
   * @returns {Promise<Object>} API response
   */
  async getRevenueStatsData(year) {
    console.log(`💰 Getting revenue stats data for: ${year}`);
    return this.get(`/api/revenue-stats-data/${year}`);
  }

  // ===============================
  // SWEETALERT2 INTEGRATION
  // ===============================

  /**
   * Show loading modal with SweetAlert2
   */
  async showLoadingModal(
    title = "Đang xử lý...",
    text = "Vui lòng chờ trong giây lát"
  ) {
    return Swal.fire({
      title,
      text,
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: false,
      didOpen: () => {
        Swal.showLoading();
      },
    });
  }

  /**
   * Show success modal with SweetAlert2
   */
  async showSuccessModal(title = "Thành công!", text = "", callback = null) {
    return Swal.fire({
      icon: "success",
      title,
      text,
      confirmButtonColor: "#28a745",
    }).then(() => {
      if (callback) callback();
    });
  }

  /**
   * Show error modal with SweetAlert2
   */
  async showErrorModal(title = "Lỗi!", text = "Có lỗi xảy ra") {
    return Swal.fire({
      icon: "error",
      title,
      text,
      confirmButtonColor: "#dc3545",
    });
  }

  /**
   * Show confirmation modal with SweetAlert2
   */
  async showConfirmModal(
    title,
    text,
    confirmText = "Xác nhận",
    cancelText = "Hủy"
  ) {
    return Swal.fire({
      title,
      text,
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#dc3545",
      cancelButtonColor: "#6c757d",
      confirmButtonText: confirmText,
      cancelButtonText: cancelText,
    });
  }

  // ===============================
  // UTILITY METHODS
  // ===============================

  /**
   * Handle form submission with loading state
   * @param {HTMLFormElement} form - Form element
   * @param {Function} apiCall - API function to call
   * @param {Object} options - Additional options
   */
  async handleFormSubmission(form, apiCall, options = {}) {
    const {
      successCallback = () => {},
      errorCallback = () => {},
      successMessage = "Thao tác thành công",
      errorMessage = "Có lỗi xảy ra",
      reloadOnSuccess = true,
      reloadDelay = 1500,
    } = options;

    // Disable form during submission
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton?.textContent;

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.innerHTML =
        '<i class="fas fa-spinner fa-spin me-2"></i>Đang xử lý...';
    }

    try {
      const result = await apiCall();

      this.handleResponse(result, {
        onSuccess: (data, message) => {
          successCallback(data, message);

          if (reloadOnSuccess) {
            setTimeout(() => {
              location.reload();
            }, reloadDelay);
          }
        },
        onError: (data, message) => {
          errorCallback(data, message);
        },
        successMessage,
        errorMessage,
      });
    } catch (error) {
      console.error("Form submission error:", error);
      if (typeof showToast === "function") {
        showToast("error", "Có lỗi xảy ra khi gửi yêu cầu");
      }
      errorCallback(null, "Network error");
    } finally {
      // Restore form state
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = originalText;
      }
    }
  }

  /**
   * Handle modal form submission
   * @param {string} modalId - Modal element ID
   * @param {Function} apiCall - API function to call
   * @param {Object} options - Additional options
   */
  async handleModalFormSubmission(modalId, apiCall, options = {}) {
    const modal = document.getElementById(modalId);
    const modalInstance = modal ? bootstrap.Modal.getInstance(modal) : null;

    await this.handleFormSubmission(modal?.querySelector("form"), apiCall, {
      ...options,
      successCallback: (data, message) => {
        // Close modal on success
        if (modalInstance) {
          modalInstance.hide();
        }

        if (options.successCallback) {
          options.successCallback(data, message);
        }
      },
    });
  }
}

// Create and export singleton instance
window.AdminAPI = new AdminAPIService();

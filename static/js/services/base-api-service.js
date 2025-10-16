/**
 * Base API Service
 * Provides common functionality for all API services
 */
class BaseAPIService {
  constructor(baseURL = "") {
    this.baseURL = baseURL;
    this.defaultHeaders = {
      "Content-Type": "application/json",
    };
  }

  /**
   * Get CSRF token from meta tag
   * @returns {string|null} CSRF token
   */
  getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute("content") : null;
  }

  /**
   * Get headers with CSRF token
   * @param {Object} additionalHeaders - Additional headers to merge
   * @returns {Object} Headers object
   */
  getHeaders(additionalHeaders = {}) {
    const headers = { ...this.defaultHeaders, ...additionalHeaders };

    const csrfToken = this.getCSRFToken();
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }

    return headers;
  }

  /**
   * Make HTTP request
   * @param {string} endpoint - API endpoint
   * @param {Object} options - Fetch options
   * @returns {Promise<Object>} Response object with success, data, status
   */
  async makeRequest(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;

    const config = {
      headers: this.getHeaders(options.headers),
      ...options,
    };

    try {
      console.log(`🌐 API Request: ${config.method || "GET"} ${url}`);

      const response = await fetch(url, config);
      let data = null;

      // Try to parse JSON response
      try {
        data = await response.json();
      } catch (parseError) {
        console.warn("Response is not valid JSON:", parseError);
        data = { message: "Invalid response format" };
      }

      const result = {
        success: response.ok,
        data: data,
        status: response.status,
        statusText: response.statusText,
      };

      if (response.ok) {
        console.log(`✅ API Success: ${url}`, result);
      } else {
        console.warn(`❌ API Error: ${url}`, result);
      }

      return result;
    } catch (error) {
      console.error(`🚨 API Network Error: ${url}`, error);

      return {
        success: false,
        data: { error: error.message },
        status: 0,
        statusText: "Network Error",
        networkError: true,
      };
    }
  }

  /**
   * GET request
   * @param {string} endpoint - API endpoint
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Response object
   */
  async get(endpoint, options = {}) {
    return this.makeRequest(endpoint, {
      method: "GET",
      ...options,
    });
  }

  /**
   * POST request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request body data
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Response object
   */
  async post(endpoint, data = null, options = {}) {
    return this.makeRequest(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : null,
      ...options,
    });
  }

  /**
   * PUT request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request body data
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Response object
   */
  async put(endpoint, data = null, options = {}) {
    return this.makeRequest(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : null,
      ...options,
    });
  }

  /**
   * DELETE request
   * @param {string} endpoint - API endpoint
   * @param {Object} data - Request body data (optional)
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Response object
   */
  async delete(endpoint, data = null, options = {}) {
    return this.makeRequest(endpoint, {
      method: "DELETE",
      body: data ? JSON.stringify(data) : null,
      ...options,
    });
  }

  /**
   * Handle API response for UI operations
   * @param {Object} result - API result from makeRequest
   * @param {Object} callbacks - Success and error callbacks
   */
  handleResponse(result, callbacks = {}) {
    const {
      onSuccess = () => {},
      onError = () => {},
      successMessage = "Thao tác thành công",
      errorMessage = "Có lỗi xảy ra",
    } = callbacks;

    if (result.success) {
      const message = result.data?.message || successMessage;
      onSuccess(result.data, message);

      // Show success toast if available
      if (typeof showToast === "function") {
        showToast("success", message);
      }
    } else {
      const message = result.data?.error || errorMessage;
      onError(result.data, message);

      // Show error toast if available
      if (typeof showToast === "function") {
        showToast("error", message);
      }
    }
  }
}

// Export for use in other files
window.BaseAPIService = BaseAPIService;

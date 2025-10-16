function showToast(type, message) {
  const toastElement = document.getElementById(type + "Toast");
  if (!toastElement) {
    console.error("Không tìm thấy phần tử toast:", type + "Toast");
    return;
  }

  // Cập nhật nội dung
  const toastBody = toastElement.querySelector(".toast-body");
  if (toastBody) {
    toastBody.textContent = message;
  }

  // Khởi tạo toast Bootstrap với animation tùy chỉnh
  const toast = new bootstrap.Toast(toastElement, {
    animation: true,
    autohide: true,
    delay: 3000,
  });

  // Thêm event listeners cho animation
  toastElement.addEventListener("show.bs.toast", function () {
    this.classList.add("showing");
  });

  toastElement.addEventListener("shown.bs.toast", function () {
    this.classList.remove("showing");
    this.classList.add("show");
  });

  toastElement.addEventListener("hide.bs.toast", function () {
    this.classList.add("hiding");
    this.classList.remove("show");
  });

  toastElement.addEventListener("hidden.bs.toast", function () {
    this.classList.remove("hiding");
  });

  // Hiển thị toast
  toast.show();
}

/**
 * Password Strength Evaluation
 */
function evaluatePasswordStrength(password, strengthElement) {
  if (!password) {
    strengthElement.innerHTML = "";
    return;
  }

  // Simple client-side evaluation
  let score = 0;
  let details = [];

  // Length check
  if (password.length >= 8) {
    score += 2;
    details.push("✓ Độ dài tốt (≥ 8 ký tự)");
  } else if (password.length >= 6) {
    score += 1;
    details.push("⚠ Độ dài trung bình (6-7 ký tự)");
  } else {
    details.push("✗ Độ dài quá ngắn (≤ 5 ký tự)");
  }

  // Character types
  const hasLower = /[a-z]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasDigit = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password);

  const charTypes = [hasLower, hasUpper, hasDigit, hasSpecial].filter(
    Boolean
  ).length;

  if (charTypes >= 3) {
    score += 2;
    details.push(`✓ Sử dụng ${charTypes} loại ký tự`);
  } else if (charTypes === 2) {
    score += 1;
    details.push("⚠ Sử dụng 2 loại ký tự");
  } else {
    details.push("✗ Chỉ sử dụng 1 loại ký tự");
  }

  // Common patterns
  if (/123|abc|qwe|asd|zxc/.test(password.toLowerCase())) {
    score -= 1;
  }

  // Determine strength
  let strength, strengthClass;
  if (score <= 0) {
    strength = "YẾU";
    strengthClass = "text-danger";
  } else if (score <= 2) {
    strength = "TRUNG BÌNH";
    strengthClass = "text-warning";
  } else {
    strength = "MẠNH";
    strengthClass = "text-success";
  }

  // Update UI
  strengthElement.innerHTML = `
        <div class="${strengthClass} fw-bold">
            <i class="bi bi-shield me-1"></i>
            Độ mạnh: ${strength}
        </div>
        <small class="text-muted">
            ${details.join("<br>")}
        </small>
    `;
}

/**
 * Check Password Match
 */
function checkPasswordMatch(passwordInput, confirmPasswordInput, matchElement) {
  const password = passwordInput.value;
  const confirmPassword = confirmPasswordInput.value;

  if (!confirmPassword) {
    matchElement.innerHTML = "";
    return;
  }

  if (password === confirmPassword) {
    matchElement.innerHTML =
      '<i class="bi bi-check-circle me-1"></i>Mật khẩu khớp';
    matchElement.className = "text-success fw-bold";
  } else {
    matchElement.innerHTML =
      '<i class="bi bi-x-circle me-1"></i>Mật khẩu không khớp';
    matchElement.className = "text-danger fw-bold";
  }
}

/**
 * Initialize Add Owner Form
 */
function initializeAddOwnerForm() {
  const modalElement = document.getElementById("addOwnerModal");
  const addOwnerForm = document.getElementById("addOwnerForm");
  let addOwnerModal = null;

  if (modalElement) {
    addOwnerModal = new bootstrap.Modal(modalElement, {
      backdrop: "static",
      keyboard: false,
    });
  }

  // Password elements
  const passwordInput = addOwnerForm
    ? addOwnerForm.querySelector("#password")
    : null;
  const confirmPasswordInput = addOwnerForm
    ? addOwnerForm.querySelector("#confirm_password")
    : null;
  const passwordStrength = addOwnerForm
    ? addOwnerForm.querySelector("#passwordStrength")
    : null;
  const passwordMatch = addOwnerForm
    ? addOwnerForm.querySelector("#passwordMatch")
    : null;

  // Password strength evaluation
  if (passwordInput) {
    passwordInput.addEventListener("input", function () {
      const password = this.value;
      if (passwordStrength) {
        evaluatePasswordStrength(password, passwordStrength);
      }
      if (confirmPasswordInput && passwordMatch) {
        checkPasswordMatch(passwordInput, confirmPasswordInput, passwordMatch);
      }
    });
  }

  if (confirmPasswordInput) {
    confirmPasswordInput.addEventListener("input", function () {
      if (passwordInput && passwordMatch) {
        checkPasswordMatch(passwordInput, confirmPasswordInput, passwordMatch);
      }
    });
  }

  // Form submission - DISABLED (using SweetAlert2 instead)
  // if (addOwnerForm) {
  //   addOwnerForm.addEventListener("submit", async function (e) {
  //     // ... old code removed to avoid duplication
  //   });
  // }

  // Reset form when modal is closed
  const addOwnerModalElement = document.getElementById("addOwnerModal");
  if (addOwnerModalElement) {
    addOwnerModalElement.addEventListener("hidden.bs.modal", function () {
      if (addOwnerForm) {
        addOwnerForm.reset();
        const inputs = addOwnerForm.querySelectorAll("input");
        inputs.forEach((input) => {
          input.classList.remove("is-invalid");
          if (input.nextElementSibling) {
            input.nextElementSibling.textContent = "";
          }
        });

        // Clear password strength indicators
        if (passwordStrength) passwordStrength.innerHTML = "";
        if (passwordMatch) passwordMatch.innerHTML = "";
      }
    });
  }
}

/**
 * Initialize Add Admin Form
 */
function initializeAddAdminForm() {
  const addAdminModal = document.getElementById("addAdminModal");
  const addAdminForm = document.getElementById("addAdminForm");
  const submitAddAdminBtn = document.getElementById("submitAddAdmin");

  if (addAdminForm && submitAddAdminBtn) {
    submitAddAdminBtn.addEventListener("click", async function () {
      // Validate form
      if (!addAdminForm.checkValidity()) {
        addAdminForm.reportValidity();
        return;
      }

      // Check if passwords match
      const password = document.getElementById("adminPassword").value;
      const confirmPassword = document.getElementById(
        "adminConfirmPassword"
      ).value;
      const confirmPasswordField = document.getElementById(
        "adminConfirmPassword"
      );

      if (password !== confirmPassword) {
        confirmPasswordField.classList.add("is-invalid");
        return;
      } else {
        confirmPasswordField.classList.remove("is-invalid");
      }

      const formData = {
        username: document.getElementById("adminUsername").value.trim(),
        email: document.getElementById("adminEmail").value.trim(),
        password: password,
        confirm_password: confirmPassword,
        role: document.getElementById("adminRole").value,
      };

      try {
        // Use AdminAPI service for cleaner code
        const result = await window.AdminAPI.addAdmin(formData);

        if (result.success) {
          const message = result.data.message || "Thêm admin mới thành công!";
          showToast("success", message);
          const bsModal = bootstrap.Modal.getInstance(addAdminModal);
          bsModal.hide();

          // Reload page after a short delay to show the new admin
          setTimeout(() => {
            location.reload();
          }, 1500);
        } else {
          const errorMessage =
            result.data.error || "Đã xảy ra lỗi khi thêm admin";
          showToast("error", errorMessage);
        }
      } catch (error) {
        console.error("Error:", error);
        showToast("error", "Đã xảy ra lỗi khi gửi yêu cầu");
      }
    });

    // Reset form when modal is closed
    addAdminModal.addEventListener("hidden.bs.modal", function () {
      addAdminForm.reset();

      // Remove any validation errors
      const inputs = addAdminForm.querySelectorAll(".form-control");
      inputs.forEach((input) => {
        input.classList.remove("is-invalid");
      });
    });
  }
}

/**
 * Initialize Commission Update Handlers
 */
function initializeCommissionHandlers() {
  // Commission update for individual rooms (modal chi tiết)
  $(document).on("click", ".btn-save-commission", function () {
    var roomId = $(this).data("room-id");
    var input = $('.commission-input[data-room-id="' + roomId + '"]');
    var percent = input.val();
    var btn = $(this);
    btn.prop("disabled", true);

    $.ajax({
      url: "/admin/api/room/" + roomId + "/commission",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ commission_percent: percent }),
      success: function (res) {
        if (res.success) {
          input.val(res.commission_percent);
          if (window.notificationSystem) {
            window.notificationSystem.showCustomNotification(
              res.message || "Cập nhật hoa hồng thành công!",
              "success"
            );
          } else {
            showToast(
              "success",
              res.message || "Cập nhật hoa hồng thành công!"
            );
          }
        } else {
          if (window.notificationSystem) {
            window.notificationSystem.showCustomNotification(
              res.error || "Có lỗi xảy ra!",
              "error"
            );
          } else {
            showToast("error", res.error || "Có lỗi xảy ra!");
          }
        }
      },
      error: function (xhr) {
        if (window.notificationSystem) {
          window.notificationSystem.showCustomNotification(
            "Có lỗi xảy ra khi kết nối server!",
            "error"
          );
        } else {
          showToast("error", "Có lỗi xảy ra khi kết nối server!");
        }
      },
      complete: function () {
        btn.prop("disabled", false);
      },
    });
  });

  // Commission update for owners (bảng user)
  $(document).on("click", ".btn-save-commission-owner", function () {
    var ownerId = $(this).data("owner-id");
    var input = $('.commission-owner-input[data-owner-id="' + ownerId + '"]');
    var percent = input.val();
    var btn = $(this);
    btn.prop("disabled", true);

    $.ajax({
      url: "/admin/api/owner/" + ownerId + "/commission",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ commission_percent: percent }),
      success: function (res) {
        if (res.success) {
          input.val(res.commission_percent);
          if (window.notificationSystem) {
            window.notificationSystem.showCustomNotification(
              res.message || "Cập nhật hoa hồng thành công!",
              "success"
            );
          } else {
            showToast(
              "success",
              res.message || "Cập nhật hoa hồng thành công!"
            );
          }
        } else {
          if (window.notificationSystem) {
            window.notificationSystem.showCustomNotification(
              res.error || "Có lỗi xảy ra!",
              "error"
            );
          } else {
            showToast("error", res.error || "Có lỗi xảy ra!");
          }
        }
      },
      error: function (xhr) {
        if (window.notificationSystem) {
          window.notificationSystem.showCustomNotification(
            "Có lỗi xảy ra khi kết nối server!",
            "error"
          );
        } else {
          showToast("error", "Có lỗi xảy ra khi kết nối server!");
        }
      },
      complete: function () {
        btn.prop("disabled", false);
      },
    });
  });
}

/**
 * Initialize Forms
 */
function initializeForms() {
  initializeAddOwnerForm();
  initializeAddAdminForm();
  initializeCommissionHandlers();
}

// Export functions for global access
window.showToast = showToast;
window.evaluatePasswordStrength = evaluatePasswordStrength;
window.checkPasswordMatch = checkPasswordMatch;

// Auto-initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", initializeForms);

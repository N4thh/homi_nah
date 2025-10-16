/**
 * Handle under development feature notifications
 */

let currentToast = null;

// Function to show development notification with specific feature name
function showDevelopmentNotification(featureId) {
  // If there's an existing toast, close it
  if (currentToast) {
    currentToast.close();
  }

  // Map of feature IDs to their display names
  const featureNames = {
    "menu-homestay": "Quản lý Homestay",
    "menu-booking": "Quản lý đặt phòng",
    "menu-payment": "Quản lý thanh toán",
    "menu-report": "Báo cáo",
  };

  // Create new toast
  const Toast = Swal.mixin({
    toast: true,
    position: "top-end",
    showConfirmButton: false,
    timer: 2000,
    timerProgressBar: true,
    didOpen: (toast) => {
      toast.addEventListener("mouseenter", Swal.stopTimer);
      toast.addEventListener("mouseleave", Swal.resumeTimer);
    },
    willClose: () => {
      currentToast = null;
    },
  });

  // Get feature name from map or use a default
  const featureName = featureNames[featureId] || "Tính năng này";

  // Show new notification and store reference
  currentToast = Toast.fire({
    icon: "info",
    title: `${featureName} đang được phát triển`,
    background: "#fff",
    customClass: {
      popup: "my-toast",
    },
  });
}

// Add event listeners when document is ready
document.addEventListener("DOMContentLoaded", function () {
  // Map of menu items to their IDs
  const menuItems = {
    "menu-homestay": true,
    "menu-booking": true,
    "menu-payment": true,
    "menu-report": true,
  };

  // Add click handler to each menu item that needs development notification
  Object.keys(menuItems).forEach((menuId) => {
    const element = document.getElementById(menuId);
    if (element) {
      element.addEventListener("click", function (e) {
        e.preventDefault();
        showDevelopmentNotification(menuId);
      });
    }
  });
});

// AJAX Functions for Smart Parking System

// Generic AJAX request function
function ajaxRequest(url, method, data, successCallback, errorCallback) {
    const csrftoken = getCookie('csrftoken');
    
    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken,
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: data ? JSON.stringify(data) : null
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('Network response was not ok');
    })
    .then(data => {
        if (successCallback) successCallback(data);
    })
    .catch(error => {
        console.error('AJAX Error:', error);
        if (errorCallback) errorCallback(error);
    });
}

// Get cookie value by name
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Mark notification as read
function markNotificationRead(notificationId, element) {
    ajaxRequest(
        `/notifications/${notificationId}/mark-read/`,
        'POST',
        null,
        function(data) {
            if (element) {
                element.closest('.list-group-item').classList.remove('list-group-item-primary');
                const button = element.closest('.list-group-item').querySelector('.mark-read');
                if (button) button.remove();
            }
            updateNotificationCount();
        },
        function(error) {
            console.error('Error marking notification as read:', error);
        }
    );
}

// Mark all notifications as read
function markAllNotificationsRead() {
    ajaxRequest(
        '/notifications/mark-all-read/',
        'POST',
        null,
        function(data) {
            location.reload();
        },
        function(error) {
            console.error('Error marking all notifications as read:', error);
        }
    );
}

// Update notification count in navbar
function updateNotificationCount() {
    fetch('/notifications/unread-count/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        const badge = document.getElementById('notification-badge');
        if (badge) {
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
    })
    .catch(error => console.error('Error updating notification count:', error));
}

// Search available slots
function searchAvailableSlots(searchParams, callback) {
    const queryString = new URLSearchParams(searchParams).toString();
    ajaxRequest(
        `/search/api/?${queryString}`,
        'GET',
        null,
        function(data) {
            if (callback) callback(data);
        },
        function(error) {
            console.error('Error searching slots:', error);
        }
    );
}

// Create reservation via AJAX
function createReservation(reservationData, successCallback, errorCallback) {
    ajaxRequest(
        '/reservations/create/api/',
        'POST',
        reservationData,
        successCallback,
        errorCallback
    );
}

// Cancel reservation
function cancelReservation(reservationId, successCallback, errorCallback) {
    ajaxRequest(
        `/reservations/${reservationId}/cancel/`,
        'POST',
        null,
        successCallback,
        errorCallback
    );
}

// Check in to reservation
function checkInReservation(reservationCode, successCallback, errorCallback) {
    ajaxRequest(
        '/reservations/check-in/api/',
        'POST',
        { reservation_code: reservationCode },
        successCallback,
        errorCallback
    );
}

// Check out from reservation
function checkOutReservation(reservationCode, successCallback, errorCallback) {
    ajaxRequest(
        '/reservations/check-out/api/',
        'POST',
        { reservation_code: reservationCode },
        successCallback,
        errorCallback
    );
}

// Get slot availability for a location
function getSlotAvailability(locationId, date, callback) {
    ajaxRequest(
        `/api/slots/availability/?location=${locationId}&date=${date}`,
        'GET',
        null,
        callback,
        function(error) {
            console.error('Error fetching slot availability:', error);
        }
    );
}

// Generate report
function generateReport(reportData, successCallback, errorCallback) {
    ajaxRequest(
        '/reports/generate/api/',
        'POST',
        reportData,
        successCallback,
        errorCallback
    );
}

// Export data to CSV
function exportToCSV(url, filename) {
    fetch(url, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.blob())
    .then(blob => {
        const link = document.createElement('a');
        const objectUrl = URL.createObjectURL(blob);
        link.href = objectUrl;
        link.download = filename || 'export.csv';
        link.click();
        URL.revokeObjectURL(objectUrl);
    })
    .catch(error => console.error('Export error:', error));
}

// Auto-save form data
let autoSaveTimeout;
function autoSaveForm(formId, saveUrl) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const formData = new FormData(form);
    clearTimeout(autoSaveTimeout);
    
    autoSaveTimeout = setTimeout(() => {
        ajaxRequest(
            saveUrl,
            'POST',
            Object.fromEntries(formData),
            function(data) {
                showToast('Auto-saved successfully', 'success');
            },
            function(error) {
                console.error('Auto-save failed:', error);
            }
        );
    }, 2000);
}
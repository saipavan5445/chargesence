/**
 * ChargeSense Global Application Scripts
 * Theme switching, toast notifications, navbar notifications, and browser alerts.
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initNotifications();
    initMobileSidebar();
});

/**
 * Theme Management (Dark / Light)
 */
function initTheme() {
    const savedTheme = localStorage.getItem('chargesense_theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        updateThemeIcon(savedTheme);
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('chargesense_theme', newTheme);
            updateThemeIcon(newTheme);

            // Persist to user settings via API if authenticated
            fetch('/api/settings/theme', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme: newTheme })
            }).catch(() => {});
        });
    }
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('#themeToggleBtn i');
    if (icon) {
        if (theme === 'light') {
            icon.className = 'fa-solid fa-moon text-warning';
        } else {
            icon.className = 'fa-solid fa-sun text-warning';
        }
    }
}

/**
 * Toast Notification System
 */
function showToast(title, message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'toast-item';

    const iconMap = {
        success: 'fa-circle-check text-success',
        warning: 'fa-triangle-exclamation text-warning',
        danger: 'fa-circle-exclamation text-danger',
        info: 'fa-circle-info text-info'
    };

    const iconClass = iconMap[type] || iconMap.info;

    toast.innerHTML = `
        <div style="font-size: 1.3rem;"><i class="fa-solid ${iconClass}"></i></div>
        <div style="flex: 1;">
            <div style="font-weight: 700; font-size: 0.92rem; margin-bottom: 2px;">${title}</div>
            <div style="font-size: 0.82rem; color: var(--ink-secondary); line-height: 1.3;">${message}</div>
        </div>
        <button type="button" class="btn-close btn-close-white" style="font-size: 0.75rem;" onclick="this.parentElement.remove()"></button>
    `;

    container.appendChild(toast);

    // Auto dismiss after 4.5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 400);
        }
    }, 4500);

    // Optional browser notification
    sendBrowserNotification(title, message);
}

/**
 * Browser HTML5 Desktop Notifications
 */
function requestBrowserNotifications() {
    if ('Notification' in window) {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                showToast('Notifications Enabled', 'You will now receive desktop alerts for battery milestones.', 'success');
            }
        });
    }
}

function sendBrowserNotification(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') {
        try {
            new Notification(`ChargeSense: ${title}`, {
                body: body,
                icon: '/static/images/battery-icon.png'
            });
        } catch (e) {
            // Notification failed gracefully
        }
    }
}

/**
 * Navbar Notification Polling & Counter
 */
function initNotifications() {
    const unreadBadge = document.getElementById('navbarUnreadBadge');
    const notifList = document.getElementById('navbarNotifList');

    if (!unreadBadge) return;

    function fetchNotifications() {
        fetch('/api/notifications')
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    if (data.unread_count > 0) {
                        unreadBadge.textContent = data.unread_count;
                        unreadBadge.style.display = 'inline-block';
                    } else {
                        unreadBadge.style.display = 'none';
                    }

                    if (notifList && data.notifications.length > 0) {
                        notifList.innerHTML = data.notifications.slice(0, 5).map(n => `
                            <div class="p-2 border-bottom border-secondary d-flex align-items-start gap-2" style="font-size: 0.85rem;">
                                <i class="fa-solid fa-bell mt-1 ${n.notification_type === 'success' ? 'text-success' : 'text-info'}"></i>
                                <div>
                                    <div class="fw-bold text-light">${n.title}</div>
                                    <div class="text-muted" style="font-size: 0.78rem;">${n.message}</div>
                                </div>
                            </div>
                        `).join('');
                    }
                }
            })
            .catch(() => {});
    }

    fetchNotifications();
    // Refresh notifications every 15 seconds
    setInterval(fetchNotifications, 15000);
}

/**
 * Mobile Sidebar Drawer Toggler
 */
function initMobileSidebar() {
    const toggleBtn = document.getElementById('mobileSidebarToggle');
    const sidebar = document.querySelector('.app-sidebar');

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });

        // Close when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 992 && !sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }
}

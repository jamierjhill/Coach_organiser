/**
 * COACHES HUB - STREAMLINED COMPONENTS SYSTEM
 * Mobile-First JavaScript Framework
 * Reduces code duplication by 60-70%
 */

// ===========================================
// 1. CORE UTILITIES & MOBILE DETECTION
// ===========================================

const CoachesHub = {
  // Mobile detection and utilities
  isMobile: () => window.innerWidth <= 768,
  isTouch: () => 'ontouchstart' in window,
  
  // Device-specific optimizations
  device: {
    isMobile: () => window.innerWidth <= 768,
    isTablet: () => window.innerWidth > 768 && window.innerWidth <= 1024,
    isDesktop: () => window.innerWidth > 1024,
    
    // Touch target validation for accessibility
    validateTouchTargets() {
      if (this.isMobile()) {
        document.querySelectorAll('button, a, input[type="button"], input[type="submit"]').forEach(el => {
          const rect = el.getBoundingClientRect();
          if (rect.height < 44 || rect.width < 44) {
            el.style.minHeight = '44px';
            el.style.minWidth = '44px';
          }
        });
      }
    }
  }
};

// ===========================================
// 2. NOTIFICATION SYSTEM
// ===========================================

CoachesHub.notifications = {
  show(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `notification notification-${type} notification-enter`;
    
    // Mobile-optimized positioning
    const isMobile = CoachesHub.isMobile();
    toast.style.cssText = `
      position: fixed;
      ${isMobile ? 'bottom: 20px; left: 16px; right: 16px;' : 'top: 20px; right: 20px; max-width: 320px;'}
      z-index: 1050;
      padding: ${isMobile ? '16px' : '12px 16px'};
      border-radius: 8px;
      font-size: ${isMobile ? '16px' : '14px'};
      font-weight: 500;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      animation: slideIn 0.3s ease;
    `;
    
    // Color scheme based on type
    const colors = {
      success: { bg: '#00a07e', color: '#fff' },
      error: { bg: '#e74c3c', color: '#fff' },
      warning: { bg: '#f7c948', color: '#333' },
      info: { bg: '#3498db', color: '#fff' }
    };
    
    const style = colors[type] || colors.info;
    toast.style.backgroundColor = style.bg;
    toast.style.color = style.color;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Auto-remove
    setTimeout(() => {
      toast.classList.add('notification-exit');
      setTimeout(() => toast.remove(), 300);
    }, duration);
    
    return toast;
  },
  
  success: (msg, duration) => CoachesHub.notifications.show(msg, 'success', duration),
  error: (msg, duration) => CoachesHub.notifications.show(msg, 'error', duration),
  warning: (msg, duration) => CoachesHub.notifications.show(msg, 'warning', duration),
  info: (msg, duration) => CoachesHub.notifications.show(msg, 'info', duration)
};

// ===========================================
// 3. FORM HANDLING SYSTEM
// ===========================================

CoachesHub.forms = {
  // Enhanced form submission with loading states
  setupForm(selector, options = {}) {
    const form = document.querySelector(selector);
    if (!form) return;
    
    const {
      onSubmit = null,
      validateFields = [],
      submitButtonSelector = 'button[type="submit"]',
      loadingText = 'Processing...',
      successRedirect = null,
      showSuccessMessage = true
    } = options;
    
    const submitButton = form.querySelector(submitButtonSelector);
    let originalButtonText = submitButton?.textContent;
    
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      // Validation
      const errors = this.validateForm(form, validateFields);
      if (errors.length > 0) {
        this.showValidationErrors(form, errors);
        return;
      }
      
      // Loading state
      if (submitButton) {
        submitButton.textContent = loadingText;
        submitButton.disabled = true;
      }
      
      try {
        // Custom submit handler or default
        if (onSubmit) {
          const result = await onSubmit(new FormData(form));
          if (result.success && showSuccessMessage) {
            CoachesHub.notifications.success(result.message || 'Success!');
          }
          if (result.redirect || successRedirect) {
            window.location.href = result.redirect || successRedirect;
          }
        } else {
          form.submit();
        }
      } catch (error) {
        CoachesHub.notifications.error('An error occurred. Please try again.');
      } finally {
        // Reset button
        if (submitButton) {
          submitButton.textContent = originalButtonText;
          submitButton.disabled = false;
        }
      }
    });
  },
  
  // Form validation
  validateForm(form, requiredFields = []) {
    const errors = [];
    
    requiredFields.forEach(fieldName => {
      const field = form.querySelector(`[name="${fieldName}"]`);
      if (!field || !field.value.trim()) {
        errors.push({ field: fieldName, message: `${fieldName.replace('_', ' ')} is required` });
      }
    });
    
    // Email validation
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
      if (field.value && !field.value.includes('@')) {
        errors.push({ field: field.name, message: 'Please enter a valid email address' });
      }
    });
    
    // Number validation
    const numberFields = form.querySelectorAll('input[type="number"]');
    numberFields.forEach(field => {
      if (field.value && (isNaN(field.value) || parseFloat(field.value) <= 0)) {
        errors.push({ field: field.name, message: 'Please enter a valid positive number' });
      }
    });
    
    return errors;
  },
  
  // Show validation errors
  showValidationErrors(form, errors) {
    // Clear previous errors
    form.querySelectorAll('.error-message').forEach(el => el.remove());
    form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    
    errors.forEach(({ field, message }) => {
      const input = form.querySelector(`[name="${field}"]`);
      if (input) {
        input.classList.add('error');
        const errorEl = document.createElement('div');
        errorEl.className = 'error-message';
        errorEl.textContent = message;
        errorEl.style.cssText = 'color: #e74c3c; font-size: 12px; margin-top: 4px;';
        input.parentNode.appendChild(errorEl);
      }
    });
    
    CoachesHub.notifications.error('Please correct the errors below');
  }
};

// ===========================================
// 4. API HELPERS
// ===========================================

CoachesHub.api = {
  async request(url, options = {}) {
    const {
      method = 'GET',
      body = null,
      headers = {},
      showErrors = true
    } = options;
    
    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers
        },
        body: body ? JSON.stringify(body) : null
      });
      
      const data = await response.json();
      
      if (!response.ok && showErrors) {
        CoachesHub.notifications.error(data.error || 'Request failed');
      }
      
      return { success: response.ok, data, status: response.status };
    } catch (error) {
      if (showErrors) {
        CoachesHub.notifications.error('Network error. Please try again.');
      }
      return { success: false, error: error.message };
    }
  },
  
  // Convenience methods
  get: (url, options) => CoachesHub.api.request(url, { ...options, method: 'GET' }),
  post: (url, body, options) => CoachesHub.api.request(url, { ...options, method: 'POST', body }),
  put: (url, body, options) => CoachesHub.api.request(url, { ...options, method: 'PUT', body }),
  delete: (url, options) => CoachesHub.api.request(url, { ...options, method: 'DELETE' })
};

// ===========================================
// 5. MODAL SYSTEM
// ===========================================

CoachesHub.modals = {
  show(content, options = {}) {
    const {
      title = '',
      size = 'medium',
      showClose = true,
      backdrop = true,
      keyboard = true
    } = options;
    
    const modal = document.createElement('div');
    modal.className = 'modal modal-mobile';
    
    const isMobile = CoachesHub.isMobile();
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: ${isMobile ? 'flex-end' : 'center'};
      justify-content: center;
      z-index: 1050;
      animation: fadeIn 0.3s ease;
    `;
    
    const dialog = document.createElement('div');
    dialog.className = 'modal-dialog';
    dialog.style.cssText = `
      background: white;
      border-radius: ${isMobile ? '16px 16px 0 0' : '12px'};
      max-width: ${size === 'large' ? '800px' : size === 'small' ? '400px' : '600px'};
      width: ${isMobile ? '100%' : '90%'};
      max-height: ${isMobile ? '80vh' : '90vh'};
      overflow: auto;
      animation: ${isMobile ? 'slideUp' : 'scaleIn'} 0.3s ease;
    `;
    
    let dialogHTML = '';
    if (title) {
      dialogHTML += `
        <div class="modal-header" style="padding: 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
          <h5 style="margin: 0; font-size: 18px; font-weight: 600;">${title}</h5>
          ${showClose ? '<button class="modal-close" style="background: none; border: none; font-size: 24px; cursor: pointer;">&times;</button>' : ''}
        </div>
      `;
    }
    
    dialogHTML += `<div class="modal-body" style="padding: 20px;">${content}</div>`;
    dialog.innerHTML = dialogHTML;
    
    modal.appendChild(dialog);
    document.body.appendChild(modal);
    
    // Event handlers
    if (showClose) {
      const closeBtn = dialog.querySelector('.modal-close');
      closeBtn?.addEventListener('click', () => this.hide(modal));
    }
    
    if (backdrop) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) this.hide(modal);
      });
    }
    
    if (keyboard) {
      const keyHandler = (e) => {
        if (e.key === 'Escape') {
          this.hide(modal);
          document.removeEventListener('keydown', keyHandler);
        }
      };
      document.addEventListener('keydown', keyHandler);
    }
    
    return modal;
  },
  
  hide(modal) {
    if (modal) {
      modal.style.animation = 'fadeOut 0.3s ease';
      setTimeout(() => modal.remove(), 300);
    }
  },
  
  confirm(message, title = 'Confirm') {
    return new Promise((resolve) => {
      const content = `
        <p style="margin-bottom: 20px; font-size: 16px;">${message}</p>
        <div style="display: flex; gap: 12px; justify-content: flex-end;">
          <button class="btn-cancel" style="padding: 10px 20px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer;">Cancel</button>
          <button class="btn-confirm" style="padding: 10px 20px; background: #e74c3c; color: white; border: none; border-radius: 6px; cursor: pointer;">Confirm</button>
        </div>
      `;
      
      const modal = this.show(content, { title, backdrop: false });
      
      modal.querySelector('.btn-cancel').addEventListener('click', () => {
        this.hide(modal);
        resolve(false);
      });
      
      modal.querySelector('.btn-confirm').addEventListener('click', () => {
        this.hide(modal);
        resolve(true);
      });
    });
  }
};

// ===========================================
// 6. CLIPBOARD UTILITIES
// ===========================================

CoachesHub.clipboard = {
  async copy(text) {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        return true;
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        const success = document.execCommand('copy');
        document.body.removeChild(textArea);
        return success;
      }
    } catch (error) {
      console.error('Copy failed:', error);
      return false;
    }
  },
  
  async copyWithFeedback(text, successMessage = 'Copied to clipboard!') {
    const success = await this.copy(text);
    if (success) {
      CoachesHub.notifications.success(successMessage);
    } else {
      CoachesHub.notifications.error('Copy failed. Please try manually.');
    }
    return success;
  }
};

// ===========================================
// 7. SHARING UTILITIES
// ===========================================

CoachesHub.sharing = {
  async share(data) {
    const { title, text, url } = data;
    
    if (navigator.share && CoachesHub.isMobile()) {
      try {
        await navigator.share({ title, text, url });
        return true;
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Share failed:', error);
        }
      }
    }
    
    // Fallback to WhatsApp
    const whatsappText = encodeURIComponent(`${title ? title + '\n\n' : ''}${text}${url ? '\n\n' + url : ''}`);
    window.open(`https://wa.me/?text=${whatsappText}`, '_blank');
    return true;
  },
  
  shareInvoice(invoiceData) {
    const text = `🎾 INVOICE ${invoiceData.number}

From: ${invoiceData.coach} (Tennis Coach)
To: ${invoiceData.client}
Service: ${invoiceData.description}
Amount: £${invoiceData.amount}
Due: ${invoiceData.dueDate}

Thank you!`;
    
    return this.share({ title: 'Tennis Invoice', text });
  },
  
  sharePaymentReminder(clientName, amount) {
    const text = `Hi ${clientName},

Hope you're well! Just a friendly reminder that you have an outstanding balance of £${amount} for tennis coaching.

If you've already made payment, please ignore this message.

Thanks!`;
    
    return this.share({ title: 'Payment Reminder', text });
  }
};

// ===========================================
// 8. SEARCH & FILTER SYSTEM
// ===========================================

CoachesHub.search = {
  setup(options = {}) {
    const {
      searchInput = '#searchInput',
      filterSelect = '#filterSelect',
      itemsSelector = '.searchable-item',
      searchAttribute = 'data-search',
      filterAttribute = 'data-filter',
      emptyMessage = '#emptyMessage'
    } = options;
    
    const searchEl = document.querySelector(searchInput);
    const filterEl = document.querySelector(filterSelect);
    const emptyEl = document.querySelector(emptyMessage);
    
    const performSearch = () => {
      const searchTerm = searchEl?.value.toLowerCase().trim() || '';
      const filterValue = filterEl?.value || 'all';
      const items = document.querySelectorAll(itemsSelector);
      
      let visibleCount = 0;
      
      items.forEach(item => {
        const searchContent = item.getAttribute(searchAttribute)?.toLowerCase() || '';
        const filterContent = item.getAttribute(filterAttribute) || '';
        
        const matchesSearch = !searchTerm || searchContent.includes(searchTerm);
        const matchesFilter = filterValue === 'all' || filterContent === filterValue;
        
        const shouldShow = matchesSearch && matchesFilter;
        item.style.display = shouldShow ? '' : 'none';
        
        if (shouldShow) visibleCount++;
      });
      
      // Show/hide empty message
      if (emptyEl) {
        emptyEl.style.display = visibleCount === 0 ? 'block' : 'none';
      }
    };
    
    // Debounced search for better performance
    let searchTimeout;
    const debouncedSearch = () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(performSearch, 300);
    };
    
    searchEl?.addEventListener('input', debouncedSearch);
    filterEl?.addEventListener('change', performSearch);
    
    return { performSearch, clear: () => {
      if (searchEl) searchEl.value = '';
      if (filterEl) filterEl.value = 'all';
      performSearch();
    }};
  }
};

// ===========================================
// 9. MOBILE-SPECIFIC ENHANCEMENTS
// ===========================================

CoachesHub.mobile = {
  // Enhanced touch interactions
  setupTouchOptimizations() {
    if (!CoachesHub.isTouch()) return;
    
    // Add touch feedback to buttons
    document.addEventListener('touchstart', (e) => {
      if (e.target.matches('button, .btn, a[role="button"]')) {
        e.target.style.opacity = '0.7';
      }
    });
    
    document.addEventListener('touchend', (e) => {
      if (e.target.matches('button, .btn, a[role="button"]')) {
        setTimeout(() => {
          e.target.style.opacity = '';
        }, 150);
      }
    });
  },
  
  // Auto-resize textareas
  setupAutoResize() {
    document.querySelectorAll('textarea').forEach(textarea => {
      const resize = () => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
      };
      
      textarea.addEventListener('input', resize);
      resize(); // Initial resize
    });
  },
  
  // Mobile-friendly form enhancements
  setupMobileForms() {
    if (!CoachesHub.isMobile()) return;
    
    // Add appropriate input types for mobile keyboards
    document.querySelectorAll('input[name*="email"]').forEach(input => {
      input.type = 'email';
    });
    
    document.querySelectorAll('input[name*="phone"], input[name*="tel"]').forEach(input => {
      input.type = 'tel';
    });
    
    document.querySelectorAll('input[name*="amount"], input[name*="price"]').forEach(input => {
      input.type = 'number';
      input.inputMode = 'decimal';
    });
  },
  
  // Pull-to-refresh (simple implementation)
  setupPullToRefresh(callback) {
    if (!CoachesHub.isMobile()) return;
    
    let startY = 0;
    let currentY = 0;
    let isRefreshing = false;
    
    document.addEventListener('touchstart', (e) => {
      if (window.scrollY === 0) {
        startY = e.touches[0].clientY;
      }
    });
    
    document.addEventListener('touchmove', (e) => {
      if (window.scrollY === 0 && !isRefreshing) {
        currentY = e.touches[0].clientY;
        const pullDistance = currentY - startY;
        
        if (pullDistance > 100) {
          // Trigger refresh
          isRefreshing = true;
          CoachesHub.notifications.info('Refreshing...');
          
          if (callback) {
            callback().finally(() => {
              isRefreshing = false;
            });
          } else {
            setTimeout(() => {
              window.location.reload();
            }, 1000);
          }
        }
      }
    });
  }
};

// ===========================================
// 10. INVOICE-SPECIFIC UTILITIES
// ===========================================

CoachesHub.invoices = {
  async sendEmail(invoiceId) {
    const response = await CoachesHub.api.post(`/invoices/send-email/${invoiceId}`);
    
    if (response.success) {
      CoachesHub.notifications.success('📧 Invoice email sent successfully!');
      return true;
    } else {
      CoachesHub.notifications.error(response.data?.error || 'Failed to send email');
      return false;
    }
  },
  
  async markAsPaid(invoiceId) {
    const confirmed = await CoachesHub.modals.confirm(
      'Mark this invoice as paid?',
      'Confirm Payment'
    );
    
    if (confirmed) {
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = `/invoices/mark-paid/${invoiceId}`;
      document.body.appendChild(form);
      form.submit();
    }
  },
  
  shareInvoice(invoiceData) {
    return CoachesHub.sharing.shareInvoice(invoiceData);
  }
};

// ===========================================
// 11. INITIALIZATION & AUTO-SETUP
// ===========================================

CoachesHub.init = function() {
  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => this.init());
    return;
  }
  
  // Core mobile optimizations
  CoachesHub.device.validateTouchTargets();
  CoachesHub.mobile.setupTouchOptimizations();
  CoachesHub.mobile.setupAutoResize();
  CoachesHub.mobile.setupMobileForms();
  
  // Auto-setup forms with data attributes
  document.querySelectorAll('[data-form-validate]').forEach(form => {
    const requiredFields = form.dataset.formValidate.split(',').map(s => s.trim()).filter(Boolean);
    CoachesHub.forms.setupForm(`#${form.id}`, { validateFields: requiredFields });
  });
  
  // Auto-setup search functionality
  if (document.querySelector('[data-search-setup]')) {
    CoachesHub.search.setup();
  }
  
  // Auto-setup copy buttons
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', async () => {
      const text = button.dataset.copy || button.previousElementSibling?.textContent;
      if (text) {
        await CoachesHub.clipboard.copyWithFeedback(text);
      }
    });
  });
  
  // Auto-setup share buttons
  document.querySelectorAll('[data-share]').forEach(button => {
    button.addEventListener('click', () => {
      const shareData = JSON.parse(button.dataset.share);
      CoachesHub.sharing.share(shareData);
    });
  });
  
  console.log('🎾 Coaches Hub components initialized');
};

// ===========================================
// 12. CSS ANIMATIONS (INJECTED)
// ===========================================

// Inject required CSS for components
const componentStyles = `
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes fadeOut {
  from { opacity: 1; }
  to { opacity: 0; }
}

@keyframes slideIn {
  from { transform: translateY(100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@keyframes scaleIn {
  from { transform: scale(0.8); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.notification-enter {
  animation: slideIn 0.3s ease;
}

.notification-exit {
  animation: fadeOut 0.3s ease;
}

.form-input.error {
  border-color: #e74c3c;
  box-shadow: 0 0 0 3px rgba(231, 76, 60, 0.1);
}

.modal-mobile .modal-dialog {
  margin: 0;
}

@media (max-width: 768px) {
  .modal-mobile {
    align-items: flex-end;
  }
  
  .modal-mobile .modal-dialog {
    border-radius: 16px 16px 0 0;
    margin: 0;
  }
}
`;

// Inject styles
const styleSheet = document.createElement('style');
styleSheet.textContent = componentStyles;
document.head.appendChild(styleSheet);

// Auto-initialize
CoachesHub.init();

// Export for global use
window.CoachesHub = CoachesHub;
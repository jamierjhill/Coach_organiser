<script>
  // Enhanced PWA Installation Script
  let deferredPrompt;
  const installPopup = document.getElementById('installPopup');
  const installButton = document.getElementById('installButton');
  const dismissButton = document.getElementById('dismissButton');
  const closePopup = document.getElementById('closePopup');

  // Function to show the popup with animation
  function showInstallPopup() {
    installPopup.style.display = 'block';
    // Trigger reflow for animation to work
    void installPopup.offsetWidth;
    
    // Fade in the overlay
    installPopup.style.opacity = '1';
    
    // Animate the popup card
    const popupCard = document.querySelector('.install-popup');
    popupCard.style.animation = 'popIn 0.5s forwards';
  }

  // Function to hide the popup with animation
  function hideInstallPopup() {
    const popupCard = document.querySelector('.install-popup');
    popupCard.style.transform = 'translate(-50%, -50%) scale(0.9)';
    installPopup.style.opacity = '0';
    
    // Wait for animation to complete before hiding
    setTimeout(() => {
      installPopup.style.display = 'none';
      popupCard.style.transform = 'translate(-50%, -50%) scale(1)';
    }, 300);
  }

  // Listen for the beforeinstallprompt event
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    
    // Save the event so it can be triggered later
    localStorage.setItem('installPromptShown', Date.now());
    
    // Show the popup with a delay for better UX
    setTimeout(() => {
      showInstallPopup();
    }, 2000);
  });

  // Handle install button click
  installButton.addEventListener('click', async () => {
    if (deferredPrompt) {
      // Visual feedback on click
      installButton.style.transform = 'scale(0.95)';
      setTimeout(() => {
        installButton.style.transform = 'scale(1)';
      }, 150);
      
      // Show the install prompt
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`User response to the install prompt: ${outcome}`);
      deferredPrompt = null;
      
      // Hide the popup
      hideInstallPopup();
    }
  });

  // Handle dismiss button click
  dismissButton.addEventListener('click', () => {
    // Visual feedback
    dismissButton.style.opacity = '0.7';
    setTimeout(() => {
      dismissButton.style.opacity = '1';
    }, 150);
    
    hideInstallPopup();
    
    // Set a reminder to show again later
    localStorage.setItem('installLaterClicked', Date.now());
  });

  // Handle close button click
  closePopup.addEventListener('click', () => {
    hideInstallPopup();
    // Set a reminder to show again later (but longer than dismiss)
    localStorage.setItem('installClosed', Date.now());
  });

  // Hide popup if app is already installed
  window.addEventListener('appinstalled', () => {
    hideInstallPopup();
    localStorage.setItem('appInstalled', 'true');
  });

  // Check if we should show the popup based on previous user interaction
  document.addEventListener('DOMContentLoaded', () => {
    // If already installed, don't show
    if (localStorage.getItem('appInstalled') === 'true') {
      return;
    }
    
    const now = Date.now();
    const lastPrompt = parseInt(localStorage.getItem('installPromptShown') || 0);
    const lastLater = parseInt(localStorage.getItem('installLaterClicked') || 0);
    const lastClosed = parseInt(localStorage.getItem('installClosed') || 0);
    
    // Show again if "Later" was clicked more than 2 days ago
    const laterThreshold = 2 * 24 * 60 * 60 * 1000; // 2 days
    // Show again if closed more than 7 days ago
    const closedThreshold = 7 * 24 * 60 * 60 * 1000; // 7 days
    
    // Logic to determine if we should show the popup again
    if ((lastLater && now - lastLater > laterThreshold) || 
        (lastClosed && now - lastClosed > closedThreshold)) {
      if (deferredPrompt) {
        setTimeout(() => {
          showInstallPopup();
        }, 3000);
      }
    }
  });
  
  // Existing timeout script for alerts
  setTimeout(() => {
    document.querySelectorAll('.alert').forEach(alert => {
      alert.classList.remove('show');
      alert.classList.add('fade');
      setTimeout(() => alert.remove(), 500);
    });
  }, 5000);
</script>
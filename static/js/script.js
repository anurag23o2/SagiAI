/**
 * AI Image Generator Application
 * Main JavaScript file
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI components
    initializeUI();
    
    // Add event listeners
    setupEventListeners();
    
    // Initialize tooltips and popovers if using Bootstrap
    initializeBootstrapComponents();
});

/**
 * Initialize UI components and state
 */
function initializeUI() {
    // Hide result and error containers initially
    document.getElementById("result").style.display = "none";
    document.getElementById("loading").style.display = "none";
    document.getElementById("error").style.display = "none";
    
    // Apply animation to floating cards in hero section
    animateFloatingCards();
    
    // Initialize gallery if it exists
    initializeGallery();
}

/**
 * Set up all event listeners for the application
 */
function setupEventListeners() {
    // Image generation form submission
    const generateForm = document.getElementById("generateForm");
    if (generateForm) {
        generateForm.addEventListener("submit", handleImageGeneration);
    }
    
    // Gallery filter buttons
    const filterButtons = document.querySelectorAll('.filter-btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', handleGalleryFilter);
    });
    
    // Dark mode toggle
    const darkModeToggle = document.querySelector('.dark-mode-toggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
    }
    
    // Add click listeners to all action buttons
    setupActionButtons();
}

/**
 * Handle image generation form submission
 * @param {Event} event - Form submission event
 */
async function handleImageGeneration(event) {
    event.preventDefault();
    
    // Get form data
    const formData = new FormData(event.target);
    const prompt = formData.get('prompt');
    
    // Validate prompt
    if (!prompt || prompt.trim() === '') {
        showError("Please enter a prompt for the image generation");
        return;
    }
    
    // Show loading animation
    showLoading();
    
    // Hide previous results and errors
    document.getElementById("error").style.display = "none";
    document.getElementById("result").innerHTML = "";
    document.getElementById("result").style.display = "none";
    
    try {
        // API call to generate image
        const response = await fetch("/generate", {
            method: "POST",
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || "Failed to generate image");
        }
        
        // Display the generated image with fade-in animation
        displayGeneratedImage(data.image_url, prompt);
        
        // Add to gallery
        addToGallery(data.image_url, prompt);
        
        // Save to local history
        saveToHistory(data.image_url, prompt);
        
    } catch (error) {
        showError(error.message);
    } finally {
        hideLoading();
    }
}

/**
 * Display generated image with animation and action buttons
 * @param {string} imageUrl - URL of the generated image
 * @param {string} prompt - The prompt used to generate the image
 */
function displayGeneratedImage(imageUrl, prompt) {
    const resultContainer = document.getElementById("result");
    resultContainer.innerHTML = "";
    
    // Create image container
    const imageContainer = document.createElement("div");
    imageContainer.className = "image-container mb-3 fade-in";
    
    // Create image element
    const img = document.createElement("img");
    img.src = imageUrl;
    img.alt = prompt;
    img.className = "img-fluid";
    
    imageContainer.appendChild(img);
    resultContainer.appendChild(imageContainer);
    
    // Create action buttons
    const actionButtons = document.createElement("div");
    actionButtons.className = "action-buttons fade-in";
    
    // Download button
    const downloadBtn = document.createElement("button");
    downloadBtn.className = "btn btn-primary";
    downloadBtn.innerHTML = '<i class="fas fa-download me-1"></i> Download';
    downloadBtn.addEventListener('click', () => downloadImage(imageUrl, prompt));
    
    // Share button
    const shareBtn = document.createElement("button");
    shareBtn.className = "btn btn-info";
    shareBtn.innerHTML = '<i class="fas fa-share-alt me-1"></i> Share';
    shareBtn.addEventListener('click', () => shareImage(imageUrl));
    
    // Save to gallery button
    const saveBtn = document.createElement("button");
    saveBtn.className = "btn btn-success";
    saveBtn.innerHTML = '<i class="fas fa-star me-1"></i> Save to Gallery';
    saveBtn.addEventListener('click', () => saveToGallery(imageUrl, prompt));
    
    // Generate similar button
    const similarBtn = document.createElement("button");
    similarBtn.className = "btn btn-secondary";
    similarBtn.innerHTML = '<i class="fas fa-magic me-1"></i> Generate Similar';
    similarBtn.addEventListener('click', () => generateSimilar(prompt));
    
    // Add buttons to container
    actionButtons.appendChild(downloadBtn);
    actionButtons.appendChild(shareBtn);
    actionButtons.appendChild(saveBtn);
    actionButtons.appendChild(similarBtn);
    
    resultContainer.appendChild(actionButtons);
    
    // Show result container
    resultContainer.style.display = "block";
}

/**
 * Add generated image to the gallery
 * @param {string} imageUrl - URL of the generated image
 * @param {string} prompt - The prompt used to generate the image
 */
function addToGallery(imageUrl, prompt) {
    const galleryContainer = document.getElementById("galleryContainer");
    const emptyGallery = document.getElementById("galleryEmpty");
    
    if (!galleryContainer) return;
    
    // Hide empty gallery message if it exists
    if (emptyGallery) {
        emptyGallery.style.display = "none";
    }
    
    // Create gallery item
    const galleryItem = document.createElement("div");
    galleryItem.className = "col-lg-4 col-md-6 mb-4 fade-in";
    
    const currentDate = new Date().toLocaleDateString();
    const category = determineImageCategory(prompt);
    
    galleryItem.setAttribute('data-category', category);
    
    // Create gallery item HTML structure
    galleryItem.innerHTML = `
        <div class="gallery-item">
            <img src="${imageUrl}" alt="${prompt}">
            <div class="gallery-item-overlay">
                <div class="gallery-prompt">${prompt}</div>
                <div class="gallery-date">${currentDate}</div>
            </div>
            <div class="gallery-actions">
                <button class="gallery-action-btn" title="Download" onclick="downloadImage('${imageUrl}', '${prompt}')">
                    <i class="fas fa-download"></i>
                </button>
                <button class="gallery-action-btn" title="Share" onclick="shareImage('${imageUrl}')">
                    <i class="fas fa-share-alt"></i>
                </button>
                <button class="gallery-action-btn" title="Delete" onclick="removeFromGallery(this)">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `;
    
    // Add to gallery
    galleryContainer.insertBefore(galleryItem, galleryContainer.firstChild);
}

/**
 * Save image to history (recent generations)
 * @param {string} imageUrl - URL of the generated image
 * @param {string} prompt - The prompt used to generate the image
 */
function saveToHistory(imageUrl, prompt) {
    const historyImages = document.getElementById("historyImages");
    if (!historyImages) return;
    
    // Create history item
    const historyItem = document.createElement("div");
    historyItem.className = "col-md-4 col-sm-6 mb-3 history-item fade-in";
    
    // Create image container
    const imgContainer = document.createElement("div");
    imgContainer.className = "image-container";
    
    // Create image
    const historyImg = document.createElement("img");
    historyImg.src = imageUrl;
    historyImg.alt = prompt;
    historyImg.className = "img-fluid";
    historyImg.title = prompt;
    
    imgContainer.appendChild(historyImg);
    historyItem.appendChild(imgContainer);
    
    // Add to history
    historyImages.insertBefore(historyItem, historyImages.firstChild);
    
    // Limit history to 6 items
    while (historyImages.children.length > 6) {
        historyImages.removeChild(historyImages.lastChild);
    }
}

/**
 * Handle gallery filtering
 * @param {Event} e - Click event
 */
function handleGalleryFilter(e) {
    const filterButtons = document.querySelectorAll('.filter-btn');
    const galleryItems = document.querySelectorAll('[data-category]');
    const category = e.target.getAttribute('data-filter');
    
    // Update active button
    filterButtons.forEach(btn => {
        btn.classList.remove('active');
    });
    e.target.classList.add('active');
    
    // Filter gallery items
    galleryItems.forEach(item => {
        if (category === 'all' || item.getAttribute('data-category') === category) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

/**
 * Determine image category based on prompt
 * @param {string} prompt - The generation prompt
 * @returns {string} - Category name
 */
function determineImageCategory(prompt) {
    const lowerPrompt = prompt.toLowerCase();
    
    if (lowerPrompt.includes('landscape') || lowerPrompt.includes('nature') || lowerPrompt.includes('scenery')) {
        return 'landscape';
    } else if (lowerPrompt.includes('portrait') || lowerPrompt.includes('person') || lowerPrompt.includes('face')) {
        return 'portrait';
    } else if (lowerPrompt.includes('abstract') || lowerPrompt.includes('artistic')) {
        return 'abstract';
    } else if (lowerPrompt.includes('animal') || lowerPrompt.includes('creature')) {
        return 'animal';
    } else {
        return 'other';
    }
}

/**
 * Initialize gallery if it exists
 */
function initializeGallery() {
    const galleryContainer = document.getElementById('galleryContainer');
    if (!galleryContainer) return;
    
    const hasItems = galleryContainer.children.length > 0;
    const emptyGallery = document.getElementById('galleryEmpty');
    
    if (emptyGallery) {
        emptyGallery.style.display = hasItems ? 'none' : 'block';
    }
}

/**
 * Remove item from gallery
 * @param {HTMLElement} button - The clicked delete button
 */
function removeFromGallery(button) {
    const galleryItem = button.closest('.col-lg-4');
    
    // Add fade-out animation class
    galleryItem.classList.add('fade-out');
    
    // Remove after animation completes
    setTimeout(() => {
        galleryItem.remove();
        
        // Check if gallery is empty
        const galleryContainer = document.getElementById('galleryContainer');
        const emptyGallery = document.getElementById('galleryEmpty');
        
        if (galleryContainer && emptyGallery && galleryContainer.children.length === 0) {
            emptyGallery.style.display = 'block';
        }
    }, 500);
}

/**
 * Download generated image
 * @param {string} imageUrl - URL of the image to download
 * @param {string} prompt - The prompt used to generate the image
 */
function downloadImage(imageUrl, prompt) {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `ai-image-${prompt.substring(0, 20).replace(/\s+/g, '-')}-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Share image using Web Share API or fallback
 * @param {string} imageUrl - URL of the image to share
 */
function shareImage(imageUrl) {
    if (navigator.share) {
        navigator.share({
            title: 'AI Generated Image',
            text: 'Check out this AI generated image!',
            url: imageUrl
        })
        .catch(error => {
            showError('Error sharing: ' + error);
        });
    } else {
        // Fallback - copy to clipboard
        navigator.clipboard.writeText(imageUrl)
            .then(() => {
                showToast('Image URL copied to clipboard');
            })
            .catch(err => {
                showError('Failed to copy URL');
            });
    }
}

/**
 * Save image to gallery with persistent storage
 * @param {string} imageUrl - URL of the image to save
 * @param {string} prompt - The prompt used to generate the image
 */
function saveToGallery(imageUrl, prompt) {
    // In a real app, you would save to a database
    // For now, we'll just show a success message
    addToGallery(imageUrl, prompt);
    showToast('Image saved to gallery');
}

/**
 * Generate similar image by using the same prompt
 * @param {string} prompt - The original prompt
 */
function generateSimilar(prompt) {
    // Fill the prompt input with the previous prompt
    const promptInput = document.getElementById('promptInput');
    if (promptInput) {
        promptInput.value = prompt;
        
        // Scroll to the generator section
        const generatorSection = document.getElementById('generatorSection');
        if (generatorSection) {
            generatorSection.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Optional: automatically submit after a delay
        // setTimeout(() => {
        //     document.getElementById('generateForm').dispatchEvent(new Event('submit'));
        // }, 1000);
    }
}

/**
 * Setup action buttons for interactive elements
 */
function setupActionButtons() {
    // Setup gallery item actions, already handled by inline onclick events
    
    // Newsletter form submission
    const newsletterForm = document.getElementById('newsletterForm');
    if (newsletterForm) {
        newsletterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const emailInput = this.querySelector('input[type="email"]');
            if (emailInput && emailInput.value) {
                showToast('Thanks for subscribing!');
                emailInput.value = '';
            }
        });
    }
}

/**
 * Show loading animation
 */
function showLoading() {
    const loading = document.getElementById("loading");
    if (loading) {
        loading.style.display = "block";
    }
}

/**
 * Hide loading animation
 */
function hideLoading() {
    const loading = document.getElementById("loading");
    if (loading) {
        loading.style.display = "none";
    }
}

/**
 * Show error message
 * @param {string} message - Error message to display
 */
function showError(message) {
    const errorElement = document.getElementById("error");
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = "block";
    }
}

/**
 * Show toast notification
 * @param {string} message - Message to display in toast
 */
function showToast(message) {
    // Check if toast container exists, if not create it
    let toastContainer = document.getElementById('toastContainer');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 9999;';
        document.body.appendChild(toastContainer);
    }
    
    const toast = document.createElement('div');
    toast.className = 'fade-in';
    toast.style.cssText = `
        background-color: var(--card-bg);
        color: var(--text);
        padding: 12px 20px;
        border-radius: 8px;
        margin-top: 10px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        border-left: 4px solid var(--primary);
    `;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // Remove toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('fade-in');
        toast.classList.add('fade-out');
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    }, 3000);
}

/**
 * Toggle dark/light mode
 */
function toggleDarkMode() {
    // In a real implementation, you would toggle classes on the html/body element
    // For this demo, we'll just show a toast since we only have dark mode
    showToast('Dark mode is the only available theme');
}

/**
 * Initialize Bootstrap components if available
 */
function initializeBootstrapComponents() {
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Initialize popovers if Bootstrap is available
    if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
}

/**
 * Animate floating cards in hero section
 */
function animateFloatingCards() {
    const floatingCards = document.querySelectorAll('.floating-cards .card-item');
    if (floatingCards.length === 0) return;
    
    // We're using CSS animations defined in the CSS file
    // This function could be used to add random delays or custom animations
}

// Export functions that need to be accessed globally
window.downloadImage = downloadImage;
window.shareImage = shareImage;
window.removeFromGallery = removeFromGallery;
window.saveToGallery = saveToGallery;
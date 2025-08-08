// Multi-Account Upload Functionality

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const postingModeRadios = document.getElementsByName('posting_mode');
    const postTypeRadios = document.getElementsByName('post_type');
    const scheduleTypeRadios = document.getElementsByName('schedule_type');
    const singleAccountSelect = document.getElementById('singleAccountSelect');
    const multiAccountSelect = document.getElementById('multiAccountSelect');
    const singleImageUpload = document.getElementById('singleImageUpload');
    const carouselImageUpload = document.getElementById('carouselImageUpload');
    const staggerOptions = document.getElementById('staggerOptions');
    const multiAccountSummary = document.getElementById('multiAccountSummary');
    const selectedAccountsPreview = document.querySelector('.selected-accounts-preview');
    
    // File inputs
    const singleFileInput = document.getElementById('file');
    const carouselFileInput = document.getElementById('carousel_files');
    const uploadZone = document.getElementById('uploadZone');
    const carouselUploadZone = document.getElementById('carouselUploadZone');
    
    // State
    let selectedFiles = [];
    let carouselFiles = [];
    
    // Posting mode change handler
    postingModeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'single') {
                singleAccountSelect.style.display = 'block';
                multiAccountSelect.style.display = 'none';
                multiAccountSummary.style.display = 'none';
                document.getElementById('account_id').required = true;
                // Hide stagger option
                document.querySelector('label[for="schedule_stagger"]').parentElement.style.display = 'none';
            } else {
                singleAccountSelect.style.display = 'none';
                multiAccountSelect.style.display = 'block';
                multiAccountSummary.style.display = 'block';
                document.getElementById('account_id').required = false;
                // Show stagger option
                document.querySelector('label[for="schedule_stagger"]').parentElement.style.display = 'block';
            }
            updateMultiAccountSummary();
        });
    });
    
    // Post type change handler
    postTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'carousel') {
                singleImageUpload.style.display = 'none';
                carouselImageUpload.style.display = 'block';
            } else {
                singleImageUpload.style.display = 'block';
                carouselImageUpload.style.display = 'none';
            }
            updateMultiAccountSummary();
        });
    });
    
    // Schedule type change handler
    scheduleTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === 'stagger') {
                staggerOptions.style.display = 'block';
            } else {
                staggerOptions.style.display = 'none';
            }
            updateMultiAccountSummary();
        });
    });
    
    // Multi-account checkbox handler
    document.querySelectorAll('.multi-account-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSelectedAccountsPreview();
            updateMultiAccountSummary();
        });
    });
    
    // Single file upload handlers
    setupFileUpload(uploadZone, singleFileInput, false);
    
    // Carousel file upload handlers
    setupFileUpload(carouselUploadZone, carouselFileInput, true);
    
    // File upload setup function
    function setupFileUpload(zone, input, isMultiple) {
        // Click handler
        zone.addEventListener('click', function(e) {
            if (!e.target.closest('button')) {
                e.preventDefault();
                input.click();
            }
        });
        
        // Drag and drop handlers
        zone.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.add('dragover');
        });
        
        zone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('dragover');
        });
        
        zone.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                if (isMultiple) {
                    handleCarouselFiles(files);
                } else {
                    handleSingleFile(files[0]);
                }
            }
        });
        
        // File input change handler
        input.addEventListener('change', function(e) {
            if (isMultiple) {
                handleCarouselFiles(e.target.files);
            } else {
                handleSingleFile(e.target.files[0]);
            }
        });
    }
    
    // Handle single file selection
    function handleSingleFile(file) {
        if (!file || !file.type.startsWith('image/')) {
            alert('Please select a valid image file.');
            return;
        }
        
        selectedFiles = [file];
        
        // Update upload zone
        uploadZone.innerHTML = `
            <i class="fas fa-check-circle fa-2x text-success mb-2"></i>
            <h5 class="text-success">Image Selected</h5>
            <p class="text-muted">${file.name}</p>
            <small class="text-muted">Click to change</small>
        `;
        uploadZone.appendChild(singleFileInput);
        
        // Show preview
        const reader = new FileReader();
        reader.onload = function(e) {
            updatePostPreview(e.target.result);
        };
        reader.readAsDataURL(file);
    }
    
    // Handle carousel files selection
    function handleCarouselFiles(files) {
        const imageFiles = Array.from(files).filter(file => file.type.startsWith('image/'));
        
        if (imageFiles.length === 0) {
            alert('Please select valid image files.');
            return;
        }
        
        if (imageFiles.length > 10) {
            alert('Maximum 10 images allowed for carousel.');
            imageFiles.splice(10);
        }
        
        carouselFiles = imageFiles;
        
        // Update upload zone
        carouselUploadZone.innerHTML = `
            <i class="fas fa-check-circle fa-2x text-success mb-2"></i>
            <h5 class="text-success">${carouselFiles.length} Images Selected</h5>
            <p class="text-muted">Click to change or drag to reorder below</p>
        `;
        carouselUploadZone.appendChild(carouselFileInput);
        
        // Show carousel preview
        showCarouselPreview();
    }
    
    // Show carousel preview with reordering
    function showCarouselPreview() {
        const preview = document.getElementById('carouselPreview');
        preview.innerHTML = '<div class="row g-2" id="carouselSortable"></div>';
        const sortableContainer = document.getElementById('carouselSortable');
        
        carouselFiles.forEach((file, index) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                const col = document.createElement('div');
                col.className = 'col-4';
                col.innerHTML = `
                    <div class="position-relative">
                        <img src="${e.target.result}" class="img-fluid rounded" style="cursor: move;">
                        <span class="position-absolute top-0 start-0 badge bg-primary m-1">${index + 1}</span>
                        <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0 m-1" 
                                onclick="removeCarouselImage(${index})">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                sortableContainer.appendChild(col);
            };
            reader.readAsDataURL(file);
        });
    }
    
    // Update selected accounts preview
    function updateSelectedAccountsPreview() {
        const selectedCheckboxes = document.querySelectorAll('.multi-account-checkbox:checked');
        const preview = document.querySelector('.selected-accounts-preview');
        
        if (selectedCheckboxes.length === 0) {
            preview.innerHTML = '<p class="text-muted mb-0">No accounts selected</p>';
            return;
        }
        
        preview.innerHTML = Array.from(selectedCheckboxes).map(cb => {
            const label = cb.parentElement.textContent.trim();
            return `<span class="selected-account-tag">
                ${label}
                <span class="remove-btn" onclick="deselectAccount('${cb.value}')">&times;</span>
            </span>`;
        }).join('');
    }
    
    // Update multi-account summary
    function updateMultiAccountSummary() {
        const selectedAccounts = document.querySelectorAll('.multi-account-checkbox:checked').length;
        const postType = document.querySelector('input[name="post_type"]:checked').value;
        const scheduleType = document.querySelector('input[name="schedule_type"]:checked').value;
        
        document.getElementById('selectedAccountCount').textContent = selectedAccounts;
        document.getElementById('selectedPostType').textContent = 
            postType === 'feed' ? 'Feed Post' : 
            postType === 'story' ? 'Story' : 'Carousel';
        
        let scheduleText = 'Immediate';
        if (scheduleType === 'next_slot') {
            scheduleText = 'Next Available Slot';
        } else if (scheduleType === 'stagger') {
            const interval = document.querySelector('[name="stagger_interval"]').value;
            scheduleText = `Staggered (${interval} min apart)`;
        }
        document.getElementById('selectedSchedule').textContent = scheduleText;
    }
    
    // Update post preview
    function updatePostPreview(imageSrc) {
        const preview = document.getElementById('postPreview');
        const caption = document.getElementById('custom_text').value || 'No caption';
        
        preview.innerHTML = `
            <div class="instagram-post-preview">
                <img src="${imageSrc}" class="img-fluid mb-2" style="border-radius: 8px;">
                <div class="caption" style="font-size: 14px; line-height: 1.4;">
                    ${caption.replace(/\n/g, '<br>')}
                </div>
            </div>
        `;
    }
    
    // Form submission handler
    document.getElementById('uploadForm').addEventListener('submit', function(e) {
        const postingMode = document.querySelector('input[name="posting_mode"]:checked').value;
        const postType = document.querySelector('input[name="post_type"]:checked').value;
        
        // Validation
        if (postingMode === 'single') {
            if (!document.getElementById('account_id').value) {
                e.preventDefault();
                alert('Please select an account.');
                return;
            }
        } else {
            const selectedAccounts = document.querySelectorAll('.multi-account-checkbox:checked');
            if (selectedAccounts.length === 0) {
                e.preventDefault();
                alert('Please select at least one account.');
                return;
            }
        }
        
        // Validate files
        if (postType === 'carousel') {
            if (carouselFiles.length === 0) {
                e.preventDefault();
                alert('Please select images for the carousel.');
                return;
            }
        } else {
            if (selectedFiles.length === 0) {
                e.preventDefault();
                alert('Please select an image.');
                return;
            }
        }
        
        // Update button state
        const submitBtn = document.getElementById('submitBtn');
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Uploading...';
        submitBtn.disabled = true;
    });
});

// Global functions
function selectAllAccounts() {
    document.querySelectorAll('.multi-account-checkbox').forEach(cb => {
        cb.checked = true;
    });
    document.querySelector('.selected-accounts-preview').dispatchEvent(new Event('change'));
}

function clearAllAccounts() {
    document.querySelectorAll('.multi-account-checkbox').forEach(cb => {
        cb.checked = false;
    });
    document.querySelector('.selected-accounts-preview').dispatchEvent(new Event('change'));
}

function deselectAccount(accountId) {
    const checkbox = document.querySelector(`.multi-account-checkbox[value="${accountId}"]`);
    if (checkbox) {
        checkbox.checked = false;
        checkbox.dispatchEvent(new Event('change'));
    }
}

function removeCarouselImage(index) {
    carouselFiles.splice(index, 1);
    if (carouselFiles.length === 0) {
        document.getElementById('carouselPreview').innerHTML = '';
        document.getElementById('carouselUploadZone').innerHTML = `
            <i class="fas fa-images fa-3x text-muted mb-3"></i>
            <h4>Drag & Drop Multiple Images Here</h4>
            <p class="text-muted">or click to browse</p>
        `;
        document.getElementById('carouselUploadZone').appendChild(document.getElementById('carousel_files'));
    } else {
        showCarouselPreview();
    }
}
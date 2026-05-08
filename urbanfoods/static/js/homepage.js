// State management
let cartOpen = false;
let cartData = { items: [], subtotal: 0, total: 0 };

// Toggle cart
function toggleCart() {
    cartOpen = !cartOpen;
    const sidebar = document.getElementById('cartSidebar');
    if (cartOpen) {
        sidebar.classList.add('active');
        loadCart();
    } else {
        sidebar.classList.remove('active');
    }
}

// Load cart from server
async function loadCart() {
    try {
        const response = await fetch('/api/cart/');
        const data = await response.json();

        if (data.success) {
            cartData = data;
            updateCartUI();
        }
    } catch (error) {
        console.error('Error loading cart:', error);
    }
}

// Update cart UI
function updateCartUI() {
    const cartItems = document.getElementById('cartItems');
    const emptyCart = document.getElementById('emptyCart');
    const cartSummary = document.getElementById('cartSummary');
    const cartBadge = document.getElementById('cartBadge');

    cartBadge.textContent = cartData.cart_count || 0;

    if (cartData.items.length === 0) {
        cartItems.innerHTML = '';
        emptyCart.classList.remove('hidden');
        cartSummary.classList.add('hidden');
    } else {
        emptyCart.classList.add('hidden');
        cartSummary.classList.remove('hidden');

        cartItems.innerHTML = cartData.items.map(item => `
            <div class="flex gap-4 border-b pb-4">
                <img src="${item.image || '/static/placeholder.jpg'}" alt="${item.name}" class="w-20 h-20 object-cover rounded">
                <div class="flex-1">
                    <h3 class="font-semibold">${item.name}</h3>
                    <p class="text-orange-600 font-bold">KES ${item.price}</p>
                    <div class="flex items-center gap-2 mt-2">
                        <button onclick="updateQuantity(${item.id}, ${item.quantity - 1})" class="w-8 h-8 bg-gray-200 rounded hover:bg-gray-300">-</button>
                        <span class="w-8 text-center">${item.quantity}</span>
                        <button onclick="updateQuantity(${item.id}, ${item.quantity + 1})" class="w-8 h-8 bg-gray-200 rounded hover:bg-gray-300">+</button>
                        <button onclick="removeFromCart(${item.id})" class="ml-auto text-red-500 hover:text-red-700">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        document.getElementById('cartSubtotal').textContent = `KES ${cartData.subtotal}`;
        document.getElementById('cartTotal').textContent = `KES ${cartData.total + 20}`; // Assuming flat delivery fee of 20
    }
}

// Add to cart
async function addToCart(foodItemId, quantity) {
    try {
        const response = await fetch('/api/cart/add/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ food_item_id: foodItemId, quantity })
        });

        const data = await response.json();

        if (data.success) {
            showToast(data.message);
            document.getElementById('cartBadge').textContent = data.cart_count;
        } else {
            showToast(data.message || 'Please login to add items', 'error');
        }
    } catch (error) {
        console.error('Error adding to cart:', error);
        showToast('Please login to add items to cart', 'error');
    }
}

// Update quantity
async function updateQuantity(cartItemId, newQuantity) {
    if (newQuantity < 1) return;

    try {
        const response = await fetch('/api/cart/update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ cart_item_id: cartItemId, quantity: newQuantity })
        });

        const data = await response.json();

        if (data.success) {
            loadCart();
        }
    } catch (error) {
        console.error('Error updating cart:', error);
    }
}

// Remove from cart
async function removeFromCart(cartItemId) {
    try {
        const response = await fetch('/api/cart/remove/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ cart_item_id: cartItemId })
        });

        const data = await response.json();

        if (data.success) {
            showToast(data.message);
            loadCart();
        }
    } catch (error) {
        console.error('Error removing from cart:', error);
    }
}

// Proceed to checkout
function proceedToCheckout() {
    if (cartData.items.length === 0) return;

    document.getElementById('checkoutModal').classList.remove('hidden');
    document.getElementById('checkoutTotal').textContent = `KES ${cartData.total + 20}`; // Assuming flat delivery fee of 20

    // Pre-fill form with user profile data
    prefillCheckoutForm();
}

// Pre-fill checkout form with user profile data
function prefillCheckoutForm() {
    // This will be handled in the template
}

// Handle hostel select change
document.getElementById('hostelSelect').addEventListener('change', function(e) {
    const customHostelDiv = document.getElementById('customHostelDiv');
    const customHostelInput = document.getElementById('customHostel');

    if (e.target.value === 'other') {
        customHostelDiv.classList.remove('hidden');
        customHostelInput.required = true;
        customHostelInput.focus();
    } else {
        customHostelDiv.classList.add('hidden');
        customHostelInput.required = false;
        customHostelInput.value = '';
    }
});

// Close checkout
function closeCheckout() {
    document.getElementById('checkoutModal').classList.add('hidden');
}

// Handle checkout form submission
document.getElementById('checkoutForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const hostelSelect = document.getElementById('hostelSelect');
    const customHostelInput = document.getElementById('customHostel');

    // Use custom hostel name if "other" is selected
    const hostelValue = hostelSelect.value === 'other' ? customHostelInput.value : hostelSelect.value;

    const formData = {
        hostel: hostelValue,
        room_number: document.getElementById('roomNumber').value,
        phone_number: document.getElementById('phoneNumber').value,
        delivery_notes: document.getElementById('deliveryNotes').value
    };

    try {
        const response = await fetch('/api/order/place/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            closeCheckout();
            toggleCart();
            showToast(`Order placed! Order #${data.order_number}. Estimated delivery: ${data.estimated_delivery}`);
            document.getElementById('checkoutForm').reset();

            // Redirect to order tracking after 2 seconds
            setTimeout(() => {
                window.location.href = '/orders/';
            }, 2000);
        } else {
            showToast(data.message || 'Error placing order', 'error');
        }
    } catch (error) {
        console.error('Error placing order:', error);
        showToast('Error placing order. Please try again.', 'error');
    }
});

// Filter by category
function filterCategory(button, categoryId) {
    const items = document.querySelectorAll('.food-item');

    items.forEach(item => {
        if (categoryId === 'all' || item.dataset.category === categoryId) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });

    // Update active button
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('bg-orange-600', 'text-white');
        btn.classList.add('bg-white', 'text-gray-700', 'border', 'border-gray-200');
    });
    button.classList.remove('bg-white', 'text-gray-700', 'border', 'border-gray-200');
    button.classList.add('bg-orange-600', 'text-white');
}

// Search functionality
document.getElementById('searchInput').addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    const items = document.querySelectorAll('.food-item');

    items.forEach(item => {
        const name = item.querySelector('h3').textContent.toLowerCase();
        const description = item.querySelector('p').textContent.toLowerCase();

        if (name.includes(query) || description.includes(query)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
});

function toggleMobileMenu() {
    const menu = document.getElementById('mobileMenu');

    if (menu.classList.contains('hidden')) {
        // Show menu with animation
        menu.classList.remove('hidden');
        setTimeout(() => {
            menu.classList.remove('opacity-0', 'scale-95');
            menu.classList.add('opacity-100', 'scale-100');
        }, 10); // tiny delay so transition kicks in
    } else {
        // Hide menu with animation
        menu.classList.remove('opacity-100', 'scale-100');
        menu.classList.add('opacity-0', 'scale-95');
        setTimeout(() => {
            menu.classList.add('hidden');
        }, 300); // wait for transition to finish
    }
}

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');

    toastMessage.textContent = message;
    toast.classList.remove('hidden', 'bg-green-500', 'bg-red-500');
    toast.classList.add(type === 'success' ? 'bg-green-500' : 'bg-red-500');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// Get CSRF token
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

// Close cart when clicking outside
document.getElementById('cartSidebar').addEventListener('click', (e) => {
    if (e.target.id === 'cartSidebar') {
        toggleCart();
    }
});

// Load cart on page load if user is authenticated
document.addEventListener('DOMContentLoaded', () => {
    fetch('/api/cart/')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                document.getElementById('cartBadge').textContent = data.cart_count || 0;
            }
        });
});

// Add event listeners for category buttons
document.addEventListener('DOMContentLoaded', () => {
    // Desktop category buttons
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const categoryId = btn.dataset.category;
            filterCategory(btn, categoryId);
        });
    });

    // Mobile category dropdown
    const categoryDropdownBtn = document.getElementById('categoryDropdownBtn');
    const categoryDropdownMenu = document.getElementById('categoryDropdownMenu');
    const categoryDropdownLabel = document.getElementById('categoryDropdownLabel');

    // Toggle dropdown
    if (categoryDropdownBtn) {
        categoryDropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            categoryDropdownMenu.classList.toggle('hidden');
        });
    }

    // Handle category selection in dropdown
    document.querySelectorAll('.category-dropdown-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const categoryId = item.dataset.category;
            const categoryName = item.dataset.name;

            // Update label
            categoryDropdownLabel.textContent = categoryName;

            // Close dropdown
            categoryDropdownMenu.classList.add('hidden');

            // Filter items
            const items = document.querySelectorAll('.food-item');
            items.forEach(foodItem => {
                if (categoryId === 'all' || foodItem.dataset.category === categoryId) {
                    foodItem.style.display = 'block';
                } else {
                    foodItem.style.display = 'none';
                }
            });

            // Also update desktop buttons state
            document.querySelectorAll('.category-btn').forEach(btn => {
                if (btn.dataset.category === categoryId || (categoryId === 'all' && btn.dataset.category === 'all')) {
                    btn.classList.remove('bg-white', 'text-gray-700', 'border', 'border-gray-200');
                    btn.classList.add('bg-orange-600', 'text-white');
                } else {
                    btn.classList.remove('bg-orange-600', 'text-white');
                    btn.classList.add('bg-white', 'text-gray-700', 'border', 'border-gray-200');
                }
            });
        });
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (categoryDropdownBtn && !categoryDropdownBtn.contains(e.target) && !categoryDropdownMenu.contains(e.target)) {
            categoryDropdownMenu.classList.add('hidden');
        }
    });
});

// ==================== THEME MANAGEMENT ====================

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme') || 'auto';
    setTheme(savedTheme, false); // Don't save again
});

function toggleThemeMenu() {
    const menu = document.getElementById('themeMenu');
    menu.classList.toggle('show');
}

function setTheme(theme, save = true) {
    const html = document.documentElement;
    const themeIcon = document.getElementById('themeIcon');

    if (save) {
        localStorage.setItem('theme', theme);
    }

    if (theme === 'auto') {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        html.setAttribute('data-bs-theme', prefersDark ? 'dark' : 'light');
        themeIcon.className = 'fas fa-adjust text-lg';
    } else {
        html.setAttribute('data-bs-theme', theme);
        themeIcon.className = theme === 'dark' ? 'fas fa-moon text-lg' : 'fas fa-sun text-lg';
    }

    // Hide menu after selection
    document.getElementById('themeMenu').classList.remove('show');
}

// Listen for system theme changes when in auto mode
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
    const savedTheme = localStorage.getItem('theme') || 'auto';
    if (savedTheme === 'auto') {
        setTheme('auto', false);
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const orderNumberEl = document.getElementById('orderNumber');
    const orderNumber = orderNumberEl ? orderNumberEl.value : null;

    const ratingModalEl = document.getElementById('orderRatingModal');
    const alreadyRated = ratingModalEl?.dataset.rated === "true";

    let ratingModal = null;

    if (ratingModalEl && !alreadyRated) {
        ratingModal = new bootstrap.Modal(ratingModalEl, {
            backdrop: 'static',
            keyboard: false
        });
        ratingModal.show();
    }

    // ========================
    // Submit overall order rating
    // ========================
    const orderRatingForm = document.getElementById('orderRatingForm');
    if (orderRatingForm) {
        orderRatingForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const ratingInput = orderRatingForm.querySelector('input[name="rating"]:checked');
            const reviewEl = orderRatingForm.querySelector('textarea[name="review"]');
            const review = reviewEl ? reviewEl.value.trim() : '';

            if (!ratingInput) {
                alert('Please select a rating');
                return;
            }

            const formData = new FormData();
            formData.append('rating', ratingInput.value);
            formData.append('review', review);

            try {
                const response = await fetch(`/orders/${orderNumber}/rate/`, {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-CSRFToken': getCookie('csrftoken') }
                });

                const data = await response.json();

                if (response.ok || data.success) {
                    alert('Order rating submitted successfully');
                    orderRatingForm.querySelectorAll('input, textarea, button')
                        .forEach(el => el.disabled = true);
                    if (ratingModalEl) ratingModalEl.dataset.rated = "true";
                    if (ratingModal) ratingModal.hide();
                } else {
                    alert(data.message || 'Failed to submit order rating');
                }
            } catch (error) {
                console.error('Error submitting order rating:', error);
                alert('Error submitting order rating');
            }
        });
    }

    // ========================
    // Submit per-item reviews
    // ========================
    const foodReviewForm = document.getElementById('foodReviewForm');
    if (foodReviewForm) {
        foodReviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Prevent double submission
            const submitBtn = foodReviewForm.querySelector('button[type="submit"]');
            if (submitBtn.disabled) return;
            submitBtn.disabled = true;

            const reviews = [];
            const reviewItems = foodReviewForm.querySelectorAll('.food-review-item');

            reviewItems.forEach(item => {
                const foodItemId = item.dataset.foodItemId;
                const ratingInput = item.querySelector(`input[name="rating-${foodItemId}"]:checked`);
                const commentInput = item.querySelector(`textarea[name="comment-${foodItemId}"]`);

                if (ratingInput) {
                    reviews.push({
                        food_item_id: foodItemId,
                        rating: parseInt(ratingInput.value),
                        comment: commentInput ? commentInput.value.trim() : ''
                    });
                }
            });

            if (reviews.length === 0) {
                alert('Please provide at least one rating');
                submitBtn.disabled = false; // re-enable if validation fails
                return;
            }

            try {
                const response = await fetch(`/orders/${orderNumber}/submit_review/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(reviews)
                });

                const data = await response.json();

                if (data.success) {
                    alert('Reviews submitted successfully!');
                    reviewItems.forEach(item => {
                        item.querySelectorAll('input, textarea, button')
                            .forEach(el => el.disabled = true);
                    });
                    if (ratingModalEl) ratingModalEl.dataset.rated = "true";
                    if (ratingModal) ratingModal.hide();
                } else {
                    alert(data.message || 'Failed to submit reviews');
                    submitBtn.disabled = false; // re-enable on server error
                }
            } catch (error) {
                console.error('Error submitting reviews:', error);
                alert('Error submitting reviews');
                submitBtn.disabled = false; // re-enable on network error
            }
        });
    }

    // ========================
    // Helper: get CSRF token
    // ========================
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.slice(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
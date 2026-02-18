document.addEventListener('DOMContentLoaded', () => {
    const orderNumberEl = document.getElementById('orderNumber');
    const orderNumber = orderNumberEl ? orderNumberEl.value : null;

    const ratingModalEl = document.getElementById('orderRatingModal');

    if (ratingModalEl) {
        const ratingModal = new bootstrap.Modal(ratingModalEl, {
            backdrop: 'static',   // prevents closing by clicking outside
            keyboard: false       // prevents ESC closing
        });

        ratingModal.show();
    }

    // Submit order rating and review
    const orderRatingForm = document.getElementById('orderRatingForm');
    if (orderRatingForm) {
        orderRatingForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const rating = orderRatingForm.querySelector('input[name="rating"]:checked');
            const reviewEl = orderRatingForm.querySelector('textarea[name="review"]');
            const review = reviewEl ? reviewEl.value.trim() : '';

            if (!rating) {
                alert('Please select a rating');
                return;
            }

            const formData = new FormData();
            formData.append('rating', rating.value);
            formData.append('review', review);

            try {
                const response = await fetch(`orders/${orderNumber}/rate/`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                });
                if (response.ok) {
                    alert('Order rating submitted successfully');
                    orderRatingForm.querySelectorAll('input, textarea, button').forEach(el => el.disabled = true);
                    window.location.href = '/?t=' + Date.now();
                } else {
                    alert('Failed to submit order rating');
                }
            } catch (error) {
                console.error('Error submitting order rating:', error);
                alert('Error submitting order rating');
            }
        });
    }

    // Submit food item reviews
    const foodReviewForm = document.getElementById('foodReviewForm');
    if (foodReviewForm) {
        foodReviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();

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
                return;
            }

            try {
                const response = await fetch(`orders/${orderNumber}/submit_review/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify(reviews)
                });
                const data = await response.json();
                if (data.success) {
                    alert('Food item reviews submitted successfully');
                    reviewItems.forEach(item => {
                        item.querySelectorAll('input, textarea, button').forEach(el => el.disabled = true);
                    });
                    window.location.href = '/?t=' + Date.now();
                } else {
                    alert('Failed to submit food item reviews');
                }
            } catch (error) {
                console.error('Error submitting food item reviews:', error);
                alert('Error submitting food item reviews');
            }
        });
    }

    // Helper function to get CSRF token
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
});

// Mobile Menu Toggle Script
const menuToggle = document.getElementById('mobile-menu');
const navLinks = document.getElementById('nav-links');

menuToggle.addEventListener('click', () => {
  navLinks.classList.toggle('active');
});

// Function to scroll a specific movie row container
function scrollMovies(button, direction) {
  // Find the closest movie-row-container to the clicked button
  const row = button.closest(".featured-row").querySelector(".movie-row-container");

  // Check if row exists
  if (!row) {
    console.error("Could not find movie row container.");
    return;
  }

  const cardWidth = 235; // Adjust this width based on your actual movie card width plus margin

  // Scroll in the specified direction
  row.scrollBy({
    left: direction === 'left' ? -cardWidth : cardWidth,
    behavior: 'smooth'
  });

  console.log(`Scrolled ${direction} by ${cardWidth}px in row`, row);
}



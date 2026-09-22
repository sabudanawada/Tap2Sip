function toggleTheme(){document.body.classList.toggle("dark");localStorage.setItem("tap2sip-theme",document.body.classList.contains("dark")?"dark":"light")}
(function(){if(localStorage.getItem("tap2sip-theme")==="dark")document.body.classList.add("dark")})();
function showHelp(){document.getElementById("helpModal").classList.remove("hidden")}
function hideHelp(){document.getElementById("helpModal").classList.add("hidden")}
let cashAmount=0;
function addCash(v){cashAmount+=v;updateCash()}
function exactCash(total){cashAmount=Number(total);updateCash()}
function updateCash(){let a=document.getElementById("amountDisplay"), c=document.getElementById("changeDisplay"), h=document.getElementById("amountInput");if(a)a.textContent="₹"+cashAmount.toFixed(2);if(c)c.textContent="₹"+Math.max(cashAmount-window.cashTotal,0).toFixed(2);if(h)h.value=cashAmount}


document.addEventListener("DOMContentLoaded", function(){
  const starsWrap = document.querySelector(".stars");
  if (!starsWrap) return;

  const labels = Array.from(starsWrap.querySelectorAll("label"));
  const inputs = Array.from(starsWrap.querySelectorAll('input[name="rating"]'));
  const ratingText = document.getElementById("ratingText");

  const words = {
    1: "Needs improvement",
    2: "Could be better",
    3: "Good",
    4: "Great",
    5: "Excellent!"
  };

  let selectedRating = 0;

  function highlight(rating) {
    rating = Number(rating) || 0;

    labels.forEach((label, index) => {
      if (index < rating) {
        label.classList.add("active");
      } else {
        label.classList.remove("active");
      }
    });

    if (ratingText) {
      ratingText.textContent = rating
        ? `${rating}/5 — ${words[rating]}`
        : "Select a rating";
    }
  }

  // Hover: the star under the mouse determines the preview.
  labels.forEach((label, index) => {
    label.addEventListener("mouseenter", function() {
      highlight(index + 1);
    });

    label.addEventListener("click", function() {
      selectedRating = index + 1;
      if (inputs[index]) {
        inputs[index].checked = true;
      }
      highlight(selectedRating);
    });
  });

  // Restore selected rating after the pointer leaves the entire star row.
  starsWrap.addEventListener("mouseleave", function() {
    highlight(selectedRating);
  });

  // Also support keyboard/radio interaction.
  inputs.forEach((input, index) => {
    input.addEventListener("change", function() {
      selectedRating = index + 1;
      highlight(selectedRating);
    });
  });

  const checked = inputs.find(input => input.checked);
  if (checked) {
    selectedRating = inputs.indexOf(checked) + 1;
  }

  highlight(selectedRating);
});;;

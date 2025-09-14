function smoothScroll(e) {
	e.preventDefault();
	document.querySelector(this.getAttribute('href'))
	.scrollIntoView({
		behavior: 'smooth'
	});
}

window.addEventListener('load', function() {
	document.body.classList.remove("preload");
	document.querySelectorAll('a[href^="#"]')
	.forEach(anchor => anchor.addEventListener('click', smoothScroll));
});

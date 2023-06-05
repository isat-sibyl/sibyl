
	window.addEventListener("load", () => {
		const pages = document.querySelector("#header-pages");
		if (pages) {
			const links = pages.querySelectorAll("a");
			let longest = "";
			let longestLink = null;
			for (const link of links) {
				if (window.location.pathname.includes(link.getAttribute('href')) && link.getAttribute('href').length > longest.length) {
					longest = link.getAttribute('href');
					longestLink = link;
				}
			}
			if (longestLink) longestLink.classList.add("active");
		}
	});
	window.addEventListener("page-unload", () => {
		const active = document.querySelector(`#header-pages a.active`);
		if (active) active.classList.remove("active");
	});


	if (
		"IntersectionObserver" in window &&
		"IntersectionObserverEntry" in window &&
		"intersectionRatio" in window.IntersectionObserverEntry.prototype
	) {
	let observer = new IntersectionObserver(entries => {
		if (entries[0].boundingClientRect.y < 0) {
			document.body.classList.add("header-not-at-top");
		} else {
			document.body.classList.remove("header-not-at-top");
		}
	});
	observer.observe(document.querySelector("#header-observer"));
	}

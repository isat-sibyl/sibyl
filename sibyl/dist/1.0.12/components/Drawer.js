
	function drawerComputeActive() {
		const pages = document.querySelector("#drawer");
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
	}
	function drawerInitialComputeActive() {
		drawerComputeActive();
		window.removeEventListener("load", drawerInitialComputeActive);
	}
	window.addEventListener("load", drawerInitialComputeActive);
	window.addEventListener("prepare-unload", () => {
		const active = document.querySelector(`#drawer a.active`);
		if (active) active.classList.remove("active");
		drawerComputeActive();
	});

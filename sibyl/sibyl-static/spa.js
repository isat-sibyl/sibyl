const sibylPartialsPages = {};

function smoothScroll(e) {
	e.preventDefault();
	document.querySelector(this.getAttribute('href'))
	.scrollIntoView({
		behavior: 'smooth'
	});
}

function awaitScript(script) {
	return new Promise((resolve, reject) => {
		script.addEventListener("load", () => {
			resolve();
		});
		script.addEventListener("error", () => {
			resolve();
		});
	})
}

function standardizeLink(link) {
	return link.replace(/(\?.*)?(#.*)?\/?$/, "") + "/";
}

function changeState() {
	const href = standardizeLink(window.location.href);
	requestPageChange(href);
}

function changePage(data, promises) {
	dispatchEvent(new Event('unload'));
	const parser = new DOMParser();
	const doc = parser.parseFromString(data, "text/html");
	const content = doc.querySelector("Content");
	const scripts = doc.querySelector("Scripts");
	const styles = doc.querySelector("Styles");
	const main = document.getElementById("main");
	main.innerHTML = content.innerHTML;

	if (scripts) {
		for (const script of scripts.children) {
			if (!document.querySelector(`script[src="${script.src}"]`)) {
				const newScript = document.createElement("script");
				
				for (const attr of script.attributes) {
					newScript.setAttribute(attr.name, attr.value);
				}

				document.body.appendChild(newScript);
				promises.push(awaitScript(newScript));
			}
		}
	}

	if (styles) {
		for (const style of styles.children) {
			if (!document.querySelector(`link[href="${style.href}"]`)) {
				document.head.appendChild(style);
			}
		}
	}

	const script = doc.querySelector("body>script");
	if (script) {
		script.id = "sibyl-page-script";
		eval(script.innerHTML);
	}

	const sibylPageStyle = document.getElementById("sibyl-page-style");
	if (sibylPageStyle) {
		sibylPageStyle.remove();
	}

	const style = doc.querySelector("body>style");
	if (style) {
		const style = doc.querySelector("style");
		style.id = "sibyl-page-style";
		document.head.appendChild(style);
	}

	window.scrollTo(0, 0);
	Promise.all(promises).then(() => {
		window.requestAnimationFrame(() => {
			window.dispatchEvent(new Event('load'));
		});
	});
}

function requestPageChange(href) {
	const promises = [];
	const requirements = sibylPartialsPages[href];

	for (const requirement of requirements["scripts"]) {
		if (document.querySelector(`script[src="${requirement}"]`)) {
			continue;
		}
		const script = document.createElement("script");
		script.src = requirement;
		document.body.appendChild(script);
		promises.push(awaitScript(script));
	}

	for (const requirement of requirements["styles"]) {
		if (document.querySelector(`link[href="${requirement}"]`)) {
			continue;
		}
		const style = document.createElement("link");
		style.href = requirement;
		style.rel = "stylesheet";
		document.head.appendChild(style);
	}
	
	fetch(`${href}partial.html`)
	.then(response => response.text())
	.then((data) => changePage(data, promises));
}

function onLinkClick(e) {
	const el = e.target;
	const href = standardizeLink(el.href);
	const locale = document.getElementById("locale").innerText;
	const layout = document.getElementById("layout").innerText;
	
	if (href == window.location.href) {
		e.preventDefault();
		return;
	}
	const requirements = sibylPartialsPages[href];
	if (!requirements || requirements['locale'] != locale || requirements['layout'] != layout) {
		e.preventDefault();
		return;
	}

	e.preventDefault();

	history.pushState(null, null, el.href);
	requestPageChange(href);
}

function getPages() {
	const locale = document.getElementById("locale").innerText;
	const links = [];
	const linkElements = document.querySelectorAll(`a[href^="/${locale}"]`);
	for (const link of linkElements) {
		links.push(link.href);
	}

	for (const link of links) {
		const cleanLink = standardizeLink(link);
		if (link in sibylPartialsPages) {
			continue;
		}
		fetch(`${cleanLink}partial.html.requirements.json`)
		.then(response => response.json())
		.then(data => {
			sibylPartialsPages[cleanLink] = data;
		});
	}

	for (const el of linkElements) {
		el.addEventListener("click", onLinkClick);
	}
}

window.addEventListener('load', function() {
	document.body.classList.remove("preload");
	document.querySelectorAll('a[href^="#"]')
	.forEach(anchor => anchor.addEventListener('click', smoothScroll));
	getPages();
});
window.addEventListener('unload', function() {
	document.body.classList.add("preload");
});
window.addEventListener('popstate', changeState);
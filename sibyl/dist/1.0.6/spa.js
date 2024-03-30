const sibylPartialsPages = {};
const sibylImportedDependencies = new Set();
let sibylFirstLoad = true;

function smoothScroll(e) {
	e.preventDefault();
	document.querySelector(this.getAttribute('href'))
	.scrollIntoView({
		behavior: 'smooth'
	});
}

function handleFetchResponse(response) {
	if (!response.ok) {
		throw Error(response.statusText);
	}
	return response.json();
}

function awaitScript(script) {
	return new Promise((resolve) => {
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
	dispatchEvent(new Event('page-unload'));
	const parser = new DOMParser();
	const doc = parser.parseFromString(data, "text/html");
	const content = doc.querySelector("template");
	const main = document.getElementById("main");
	const pageTitle = content.title
	if (pageTitle) {
		document.title = pageTitle;
	}
	else {
		const defaultTitle = document.getElementById("default-title");
		if (defaultTitle) {
			document.title = defaultTitle.innerText.replace(/\s/g, "");
		}
	}

	const sibylPageStyle = document.getElementById("sibyl-page-style");
	if (sibylPageStyle) {
		sibylPageStyle.remove();
	}

	main.innerHTML = content.innerHTML;

	const script = doc.querySelector("script");
	if (script) {
		eval(script.innerHTML);
	}

	const style = doc.querySelector("style");
	if (style) {
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

	dispatchEvent(new Event('prepare-unload'));

	fetch(`${href}partial.html`)
	.then(response => response.text())
	.then((data) => changePage(data, promises))
	.catch((error) => {
		console.error('Error:', error);
		window.href="/500";
	});

	for (const [key, value] of Object.entries(requirements)) {
		if (sibylImportedDependencies.has(key) || key === "locale" || key === "layout") {
			continue;
		}
		sibylImportedDependencies.add(key);
		if (value.type === "STYLE") {
			const style = document.createElement("link");
			style.rel = "stylesheet";
			style.href = value.path;
			style.type = "text/css";
			style.media = "all";
			document.head.appendChild(style);
		}
		else if (value.type === "SCRIPT") {
			const script = document.createElement("script");
			script.src = value.path;
			script.defer = true;
			document.head.appendChild(script);
			promises.push(awaitScript(script));
		}
	}
}

function onLinkClick(e) {
	e.stopPropagation();
	let el = e.target;
	while (!el.href) {
		el = el.parentElement;
	}
	const href = standardizeLink(el.href);
	const locale = document.getElementById("locale").innerText.replace(/\s/g, "");
	const layout = document.getElementById("layout").innerText.replace(/\s/g, "");

	if (href == standardizeLink(window.location.href)) {
		e.preventDefault()
		return;
	}

	const requirements = sibylPartialsPages[href];

	if (!requirements || requirements['locale'] != locale || requirements['layout'] != layout) {
		e.preventDefault()
		return;
	}

	e.preventDefault();

	history.pushState(null, null, el.href);
	requestPageChange(href);
}

function getPages() {
	const locale = document.getElementById("locale").innerText.replace(/\s/g, "");
	const links = [];
	const linkElements = document.querySelectorAll(`a[href^="/${locale}"]`);
	for (const link of linkElements) {
		links.push(link.href);
	}

	if (sibylFirstLoad) {
		const initialPage = standardizeLink(window.location.href);
		sibylPartialsPages[initialPage] = false;
		fetch(`${initialPage}partial.requirements.json`)
		.then(handleFetchResponse)
		.then(data => {
			sibylPartialsPages[initialPage] = data;
			Object.keys(data).forEach(sibylImportedDependencies.add, sibylImportedDependencies);
		})
		.catch((error) => {
			console.error('Error:', error);
		});
		sibylFirstLoad = false;
	}

	for (const link of links) {
		const cleanLink = standardizeLink(link);
		if (sibylPartialsPages[cleanLink] !== undefined) {
			continue;
		}
		sibylPartialsPages[cleanLink] = false;
		fetch(`${cleanLink}partial.requirements.json`)
		.then(handleFetchResponse)
		.then(data => {
			sibylPartialsPages[cleanLink] = data;
		})
		.catch((error) => {
			console.error('Error:', error);
		});
	}

	for (const el of linkElements) {
		el.addEventListener("click", onLinkClick);
	}
}

window.addEventListener('added-page', getPages);

window.addEventListener('load', function() {
	document.body.classList.remove("preload");
	document.querySelectorAll('a[href^="#"]')
	.forEach(anchor => anchor.addEventListener('click', smoothScroll));
	getPages();
});
window.addEventListener('page-unload', function() {
	document.body.classList.add("preload");
});
window.addEventListener('popstate', changeState);

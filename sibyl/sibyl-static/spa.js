const sibylPartialsPages = {};
const sibylImportedDependencies = Set();

function smoothScroll(e) {
	e.preventDefault();
	document.querySelector(this.getAttribute('href'))
	.scrollIntoView({
		behavior: 'smooth'
	});
}

function handleFetchResponse(response) {
	{
		if (!response.ok) {
			throw Error(response.statusText);
		}
		return response.json();
	}
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
	const content = doc.querySelector("template");
	const main = document.getElementById("main");
	const pageTitle = content.title
	if (pageTitle) {
		document.title = pageTitle.innerText;
	}
	else {
		const defaultTitle = document.getElementById("default-title");
		if (defaultTitle) {
			document.title = defaultTitle.innerText;
		}
	}
	main.innerHTML = content.innerHTML;

	for (const [key, value] of Object.entries(data)) {
		if (sibylImportedDependencies.has(key)) {
			continue;
		}
		sibylImportedDependencies.add(key);
		if (value.type === "STYLE") {
			const style = document.createElement("style");
			style.href = value.path;
			document.head.appendChild(style);
		}
		else if (value.type === "SCRIPT") {
			const script = document.createElement("script");
			script.src = value.path;
			script.defer = true;
			document.body.appendChild(script);
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
		// create a script element from the requirement
		const temp = document.createElement("div");
		temp.innerHTML = requirement;
		const script = temp.firstChild;
		if (document.querySelector(`script[src="${script.src}"]`)) {
			continue;
		}
		document.body.appendChild(script);
		promises.push(awaitScript(script));
	}

	for (const requirement of requirements["styles"]) {
		// create a link element from the requirement
		const temp = document.createElement("div");
		temp.innerHTML = requirement;
		const link = temp.firstChild;
		if (document.querySelector(`link[href="${link.href}"]`)) {
			continue;
		}
		document.head.appendChild(link);
	}
	
	fetch(`${href}partial.html`)
	.then(response => response.text())
	.then((data) => changePage(data, promises))
	.catch((error) => {
		console.error('Error:', error);
		window.href="/500";
	});
}

function onLinkClick(e) {
	const el = e.target;
	const href = standardizeLink(el.href);
	const locale = document.getElementById("locale").innerText;
	const layout = document.getElementById("layout").innerText;
	
	if (href == window.location.href) {
		return;
	}

	const requirements = sibylPartialsPages[href];	
	if (!requirements || requirements['locale'] != locale || requirements['layout'] != layout) {
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

	const initialPage = standardizeLink(window.location.href);
	sibylPartialsPages[initialPage] = false;
	fetch(`${initialPage}partial.requirements.json`)
	.then(handleFetchResponse)
	.then(data => {
		sibylPartialsPages[initialPage] = data;
		Object.keys(data).forEach(sibylImportedDependencies.add, sibylImportedDependencies);
	})

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
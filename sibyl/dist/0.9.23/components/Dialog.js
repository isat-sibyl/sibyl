
	const event = new Event('triggerDialog');

	function hideDialog() {
		for (const dialog of dialogs) {
			dialog.classList = "dialog";
		}
	}

	function showDialog(message) {
		const dialogs = document.getElementsByClassName("dialog");
		for (const dialog of dialogs) {
			dialog.classList += " active";
			dialog.innerHTML = message;
		}
		new Promise(r => setTimeout(r, 4000)).then(hide);
	}

function loadSchedule() {	
	const currentLocale = document.getElementById("locale").textContent;
	fetch("https://sessionize.com/api/v2/odookxwc/view/All", {cache: "force-cache"})
	.then((response) => response.json())
	.then((data) => {
		var sessions = {};
		var rooms = {};
		var speakers = {};
		data.rooms.forEach((room) => {
			rooms[room.id] = room.name;
		});
		data.speakers.forEach((speaker) => {
			speaker['name'] = speaker.firstName + " " + speaker.lastName;
			speaker['tagLine'] = speaker.tagLine.replace('/', '\n').replace('|', '\n').replace('||', '\n');
			speakers[speaker.id] = speaker;
		});
		data.sessions.forEach((session) => {
			const date = new Date(session.startsAt);
			const day = date.getDate();
			const time = date.getHours().toString().padStart(2, "0") + ":" + date.getMinutes().toString().padStart(2, "0");
			session['room'] = rooms[session.roomId];
			session['duration'] = (new Date(session.endsAt) - date)/1000/60;
			if (!sessions[day]) {
				sessions[day] = {};
			}
			if (!sessions[day][time]) {
				sessions[day][time] = [];
			}
			sessions[day][time].push(session);
		});

		const days = Object.keys(sessions);
		const hours = Object.keys(sessions[days[0]]);

		const dayTemplate = document.getElementById("day-template");
		const hourTemplate = document.getElementById("hour-template");
		const sessionTemplate = document.getElementById("session-template");
		const speakerTemplate = document.getElementById("speaker-template");

		const schedule = document.getElementById("schedule");
		days.forEach((day) => {
			const dayWrapper = document.createElement("div");
			schedule.appendChild(dayWrapper);
			const dayDiv = dayTemplate.cloneNode(true);
			dayDiv.removeAttribute('id');
			let weekday = new Date(Object.values(sessions[day])[0][0].startsAt).toLocaleDateString(currentLocale, {weekday: 'long'});
			weekday = weekday.charAt(0).toUpperCase() + weekday.slice(1);
			dayDiv.getElementsByClassName("day")[0].textContent = weekday;
			dayWrapper.appendChild(dayDiv);
			dayWrapper.id = "schedule-day-" + day;
			
			hours.forEach((hour) => {
				const hourWrapper = document.createElement("div");
				dayWrapper.appendChild(hourWrapper);
				const hourDiv = hourTemplate.cloneNode(true);
				hourDiv.removeAttribute('id');
				hourDiv.getElementsByClassName("hour")[0].textContent = hour;
				hourWrapper.appendChild(hourDiv);
				hourWrapper.id = dayWrapper.id + "-hour-" + hour.replace(':', '-');
				sessions[day][hour].forEach((session) => {
					const sessionDiv = sessionTemplate.cloneNode(true);
					sessionDiv.id = "session-" + session.id;
					sessionDiv.getElementsByClassName("session-title")[0].textContent = session.title;
					sessionDiv.getElementsByClassName("session-room")[0].textContent = session.room;
					sessionDiv.getElementsByClassName("session-duration")[0].textContent = session.duration + " min";
					if (session.description) {
						sessionDiv.getElementsByClassName("content")[0].textContent = session.description;
					}
					else {
						const accordion = sessionDiv.getElementsByClassName("accordion")[0];
						accordion.parentElement.removeChild(accordion);
					}
					session.speakers.forEach((speakerId) => {
						const speakerDiv = speakerTemplate.cloneNode(true);
						speakerDiv.removeAttribute('id');
						speakerDiv.getElementsByClassName("speaker-name")[0].textContent = speakers[speakerId].name;
						speakerDiv.getElementsByClassName("speaker-tagline")[0].textContent = speakers[speakerId].tagLine;
						speakerDiv.getElementsByClassName("speaker-image")[0].src = speakers[speakerId].profilePicture;
						sessionDiv.getElementsByClassName("session-speakers")[0].appendChild(speakerDiv);
					});
					hourWrapper.appendChild(sessionDiv);
				});
			});
		});
		dayTemplate.parentElement.removeChild(dayTemplate);
		hourTemplate.parentElement.removeChild(hourTemplate);
		sessionTemplate.parentElement.removeChild(sessionTemplate);
		speakerTemplate.parentElement.removeChild(speakerTemplate);

		const loader = document.getElementById("schedule-loading");
		loader.parentElement.removeChild(loader);
		const scheduleDiv = document.getElementById("schedule");
		scheduleDiv.classList.add("loaded");

		const accordions = document.getElementsByClassName('accordion');
		for (let i = 0; i < accordions.length; i++) {
			new Accordion(accordions[i]);
		}
	})
	.catch((error) => {
		const spinner = document.getElementById("schedule-loading");
		spinner.parentElement.removeChild(spinner);
		const errorDiv = document.getElementById("schedule-error");
		errorDiv.style.display = "";
		const scheduleDiv = document.getElementById("schedule");
		scheduleDiv.style.minHeight = "0";
	});
}
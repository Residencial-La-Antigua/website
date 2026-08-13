document.addEventListener("DOMContentLoaded", function () {
  var calendarEl = document.getElementById("calendar");
  if (!calendarEl) return;

  var eventsUrl = calendarEl.dataset.eventsUrl;
  var modal = document.getElementById("event-modal");

  var calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: "dayGridMonth",
    locale: "es",
    timeZone: "UTC",
    height: "auto",
    headerToolbar: {
      left: "",
      center: "title",
      right: "",
    },
    events: function (info, successCallback, failureCallback) {
      var url =
        eventsUrl +
        "?start=" +
        encodeURIComponent(info.startStr) +
        "&end=" +
        encodeURIComponent(info.endStr);
      fetch(url)
        .then(function (response) {
          return response.json();
        })
        .then(successCallback)
        .catch(failureCallback);
    },
    eventClick: function (info) {
      showEventDetail(info.event);
    },
  });

  calendar.render();

  function showEventDetail(event) {
    document.getElementById("event-modal-title").textContent = event.title;
    document.getElementById("event-modal-schedule").textContent =
      formatSchedule(event.start, event.end);

    var eventLocation = event.extendedProps.location;
    document.getElementById("event-modal-location").textContent =
      eventLocation ? "Ubicación: " + eventLocation : "";

    var description = event.extendedProps.description;
    document.getElementById("event-modal-description").textContent =
      description || "Sin descripción.";

    modal.showModal();
  }

  function formatSchedule(start, end) {
    var options = {
      dateStyle: "full",
      timeStyle: "short",
      timeZone: "UTC",
    };
    var formattedStart = new Intl.DateTimeFormat("es", options).format(start);
    if (!end) return formattedStart;
    var formattedEnd = new Intl.DateTimeFormat("es", options).format(end);
    return formattedStart + " — " + formattedEnd;
  }
});

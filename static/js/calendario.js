document.addEventListener("DOMContentLoaded", function () {
  var calendarEl = document.getElementById("calendar");
  if (!calendarEl) return;

  var eventsUrl = calendarEl.dataset.eventsUrl;
  var createUrl = calendarEl.dataset.createUrl;
  var isStaff = calendarEl.dataset.isStaff === "true";
  var modal = document.getElementById("event-modal");
  var yearSelect = document.getElementById("year-select");

  if (isStaff) calendarEl.classList.add("is-staff");

  populateYearOptions(yearSelect);

  var calendarOptions = {
    initialView: "dayGridMonth",
    locale: "es",
    timeZone: "UTC",
    height: "auto",
    headerToolbar: {
      left: "prev,next today",
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
    datesSet: function (info) {
      yearSelect.value = String(info.view.currentStart.getUTCFullYear());
    },
  };

  if (isStaff) {
    calendarOptions.dateClick = function (info) {
      showEventForm(info.dateStr);
    };
  }

  var calendar = new FullCalendar.Calendar(calendarEl, calendarOptions);

  calendar.render();

  if (isStaff) {
    setUpEventForm(calendar, createUrl);
  }

  yearSelect.addEventListener("change", function () {
    var currentDate = calendar.getDate();
    calendar.gotoDate(
      new Date(
        Date.UTC(Number(yearSelect.value), currentDate.getUTCMonth(), 1)
      )
    );
  });

  function populateYearOptions(select) {
    var currentYear = new Date().getUTCFullYear();
    for (var year = currentYear - 5; year <= currentYear + 5; year++) {
      var option = document.createElement("option");
      option.value = String(year);
      option.textContent = String(year);
      if (year === currentYear) option.selected = true;
      select.appendChild(option);
    }
  }

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

  function getCsrfToken() {
    var input = document.querySelector("#csrf-form [name=csrfmiddlewaretoken]");
    return input ? input.value : "";
  }

  function showEventForm(dateStr) {
    var formModal = document.getElementById("event-form-modal");
    var form = document.getElementById("event-form");
    form.reset();
    document.getElementById("event-form-errors").textContent = "";
    document.getElementById("event-form-start").value = dateStr + "T09:00";
    formModal.showModal();
  }

  function setUpEventForm(calendar, createUrl) {
    var formModal = document.getElementById("event-form-modal");
    var form = document.getElementById("event-form");
    var errorsEl = document.getElementById("event-form-errors");

    formModal
      .querySelector("[data-close-event-form]")
      .addEventListener("click", function () {
        formModal.close();
      });

    form.addEventListener("submit", function (submitEvent) {
      submitEvent.preventDefault();
      errorsEl.textContent = "";

      fetch(createUrl, {
        method: "POST",
        headers: { "X-CSRFToken": getCsrfToken() },
        body: new FormData(form),
      })
        .then(function (response) {
          if (response.status === 201) {
            formModal.close();
            form.reset();
            calendar.refetchEvents();
            return;
          }
          return response.json().then(function (data) {
            throw data;
          });
        })
        .catch(function (data) {
          errorsEl.textContent = formatFormErrors(data);
        });
    });
  }

  function formatFormErrors(data) {
    if (!data || !data.errors) {
      return "No se pudo guardar el evento.";
    }
    return Object.keys(data.errors)
      .map(function (field) {
        return data.errors[field]
          .map(function (error) {
            return error.message;
          })
          .join(" ");
      })
      .join(" ");
  }
});

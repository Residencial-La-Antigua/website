document.addEventListener('DOMContentLoaded', function () {
  var calendarEl = document.getElementById('calendar');
  if (!calendarEl) return;

  var eventsUrl = calendarEl.dataset.eventsUrl;
  var createUrl = calendarEl.dataset.createUrl;
  var isStaff = calendarEl.dataset.isStaff === 'true';
  var modal = document.getElementById('event-modal');
  var yearSelect = document.getElementById('year-select');

  if (isStaff) calendarEl.classList.add('is-staff');

  populateYearOptions(yearSelect);

  var calendarOptions = {
    initialView: 'dayGridMonth',
    locale: 'es',
    timeZone: 'UTC',
    height: 'auto',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: '',
    },
    events: function (info, successCallback, failureCallback) {
      var url =
        eventsUrl +
        '?start=' +
        encodeURIComponent(info.startStr) +
        '&end=' +
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
    setUpEventForm(calendar, createUrl, eventsUrl);
    setUpEventDelete(calendar, eventsUrl);
    setUpEventEdit();
    setUpRecurrenceFields();
  }

  yearSelect.addEventListener('change', function () {
    var currentDate = calendar.getDate();
    calendar.gotoDate(
      new Date(
        Date.UTC(Number(yearSelect.value), currentDate.getUTCMonth(), 1),
      ),
    );
  });

  function populateYearOptions(select) {
    var currentYear = new Date().getUTCFullYear();
    for (var year = currentYear - 5; year <= currentYear + 5; year++) {
      var option = document.createElement('option');
      option.value = String(year);
      option.textContent = String(year);
      if (year === currentYear) option.selected = true;
      select.appendChild(option);
    }
  }

  var currentEvent = null;

  function showEventDetail(event) {
    currentEvent = event;
    document.getElementById('event-modal-title').textContent = event.title;
    document.getElementById('event-modal-schedule').textContent =
      formatSchedule(event.start, event.end);

    var eventLocation = event.extendedProps.location;
    document.getElementById('event-modal-location').textContent = eventLocation
      ? 'Ubicación: ' + eventLocation
      : '';

    var description = event.extendedProps.description;
    document.getElementById('event-modal-description').textContent =
      description || 'Sin descripción.';

    modal.dataset.eventId = event.id;

    var isRecurring = !!event.extendedProps.recurringGroup;
    var deleteButton = document.getElementById('event-delete-button');
    var deleteSeriesButton = document.getElementById(
      'event-delete-series-button',
    );
    if (deleteButton) {
      resetConfirmButton(
        deleteButton,
        isRecurring ? 'Eliminar solo este' : 'Eliminar',
      );
    }
    if (deleteSeriesButton) {
      deleteSeriesButton.hidden = !isRecurring;
      resetConfirmButton(deleteSeriesButton, 'Eliminar este y los futuros');
    }

    modal.showModal();
  }

  function formatSchedule(start, end) {
    var options = {
      dateStyle: 'full',
      timeStyle: 'short',
      timeZone: 'UTC',
    };
    var formattedStart = new Intl.DateTimeFormat('es', options).format(start);
    if (!end) return formattedStart;
    var formattedEnd = new Intl.DateTimeFormat('es', options).format(end);
    return formattedStart + ' — ' + formattedEnd;
  }

  function getCsrfToken() {
    var input = document.querySelector('#csrf-form [name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  function showEventForm(dateStr) {
    var form = document.getElementById('event-form');
    form.reset();
    document.getElementById('event-form-errors').textContent = '';
    document.getElementById('event-form-heading').textContent = 'Nuevo evento';
    form.dataset.mode = 'create';
    delete form.dataset.eventId;
    document.getElementById('event-form-start').value = dateStr + 'T09:00';
    resetRecurrenceFields();
    document.getElementById('event-form-modal').showModal();
  }

  function showEventEditForm(event) {
    var form = document.getElementById('event-form');
    form.reset();
    document.getElementById('event-form-errors').textContent = '';
    document.getElementById('event-form-heading').textContent = 'Editar evento';
    form.dataset.mode = 'edit';
    form.dataset.eventId = event.id;
    document.getElementById('event-form-recurrence-section').hidden = true;

    document.getElementById('event-form-title').value = event.title;
    document.getElementById('event-form-location').value =
      event.extendedProps.location || '';
    document.getElementById('event-form-description').value =
      event.extendedProps.description || '';
    document.getElementById('event-form-start').value = toDatetimeLocalValue(
      event.start,
    );
    document.getElementById('event-form-end').value = event.end
      ? toDatetimeLocalValue(event.end)
      : '';

    modal.close();
    document.getElementById('event-form-modal').showModal();
  }

  function toDatetimeLocalValue(date) {
    return date.toISOString().slice(0, 16);
  }

  function setUpEventForm(calendar, createUrl, eventsUrl) {
    var formModal = document.getElementById('event-form-modal');
    var form = document.getElementById('event-form');
    var errorsEl = document.getElementById('event-form-errors');

    formModal
      .querySelector('[data-close-event-form]')
      .addEventListener('click', function () {
        formModal.close();
      });

    form.addEventListener('submit', function (submitEvent) {
      submitEvent.preventDefault();
      errorsEl.textContent = '';

      var isEdit = form.dataset.mode === 'edit';
      var url = isEdit
        ? eventsUrl + form.dataset.eventId + '/editar/'
        : createUrl;
      var expectedStatus = isEdit ? 200 : 201;

      fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCsrfToken() },
        body: new FormData(form),
      })
        .then(function (response) {
          if (response.status === expectedStatus) {
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

  function resetRecurrenceFields() {
    document.getElementById('event-form-recurrence-section').hidden = false;
    document.getElementById('event-form-recurrence-fields').hidden = true;
    document.getElementById('event-form-end-date').disabled = false;
    document.getElementById('event-form-occurrence-count').disabled = true;
  }

  function setUpRecurrenceFields() {
    var checkbox = document.getElementById('event-form-is-recurring');
    var fields = document.getElementById('event-form-recurrence-fields');
    var endDateInput = document.getElementById('event-form-end-date');
    var occurrenceCountInput = document.getElementById(
      'event-form-occurrence-count',
    );
    var endTypeDate = document.getElementById('event-form-end-type-date');
    var endTypeRadios = document.getElementsByName('end_type');

    checkbox.addEventListener('change', function () {
      fields.hidden = !checkbox.checked;
    });

    Array.prototype.forEach.call(endTypeRadios, function (radio) {
      radio.addEventListener('change', function () {
        endDateInput.disabled = !endTypeDate.checked;
        occurrenceCountInput.disabled = endTypeDate.checked;
        if (endTypeDate.checked) {
          occurrenceCountInput.value = '';
        } else {
          endDateInput.value = '';
        }
      });
    });
  }

  function setUpEventEdit() {
    document
      .getElementById('event-edit-button')
      .addEventListener('click', function () {
        showEventEditForm(currentEvent);
      });
  }

  function resetConfirmButton(button, defaultText) {
    button.textContent = defaultText;
    button.removeAttribute('data-confirming');
  }

  function setUpEventDelete(calendar, eventsUrl) {
    setUpTwoStepDeleteButton(
      document.getElementById('event-delete-button'),
      'Confirmar eliminación',
      function (eventId) {
        return eventsUrl + eventId + '/eliminar/';
      },
      calendar,
    );
    setUpTwoStepDeleteButton(
      document.getElementById('event-delete-series-button'),
      'Confirmar eliminación de la serie',
      function (eventId) {
        return eventsUrl + eventId + '/eliminar-serie/';
      },
      calendar,
    );
  }

  function setUpTwoStepDeleteButton(button, confirmText, buildUrl, calendar) {
    button.addEventListener('click', function () {
      if (button.dataset.confirming !== 'true') {
        button.dataset.confirming = 'true';
        button.textContent = confirmText;
        return;
      }

      fetch(buildUrl(modal.dataset.eventId), {
        method: 'DELETE',
        headers: { 'X-CSRFToken': getCsrfToken() },
      }).then(function (response) {
        if (response.status === 204) {
          modal.close();
          calendar.refetchEvents();
        }
      });
    });
  }

  function formatFormErrors(data) {
    if (!data || !data.errors) {
      return 'No se pudo guardar el evento.';
    }
    return Object.keys(data.errors)
      .map(function (field) {
        return data.errors[field]
          .map(function (error) {
            return error.message;
          })
          .join(' ');
      })
      .join(' ');
  }
});

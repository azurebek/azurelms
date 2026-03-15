(function () {
  function getCsrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  function buildReorderUrl() {
    return window.location.pathname.replace(/\/?$/, "/reorder/");
  }

  async function persistOrder(tableBody) {
    const orderedIds = Array.from(tableBody.querySelectorAll("tr[data-object-id]"))
      .map((row) => row.dataset.objectId)
      .filter(Boolean);

    const response = await fetch(buildReorderUrl(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify({ ordered_ids: orderedIds }),
    });

    if (!response.ok) {
      throw new Error("Unable to save new order.");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const tableBody = document.querySelector("#result_list tbody");
    if (!tableBody) {
      return;
    }

    const rows = Array.from(tableBody.querySelectorAll("tr")).filter((row) =>
      row.querySelector(".nav-drag-handle")
    );

    if (rows.length < 2) {
      return;
    }

    rows.forEach((row) => {
      const handle = row.querySelector(".nav-drag-handle");
      row.dataset.objectId = handle.dataset.objectId;
      row.draggable = true;
      row.classList.add("nav-sort-row");
    });

    let draggedRow = null;
    let originalOrder = rows.map((row) => row.dataset.objectId).join(",");

    tableBody.addEventListener("dragstart", function (event) {
      const handle = event.target.closest(".nav-drag-handle");
      const row = event.target.closest("tr.nav-sort-row");
      if (!handle || !row) {
        event.preventDefault();
        return;
      }

      draggedRow = row;
      draggedRow.classList.add("is-dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", row.dataset.objectId);
    });

    tableBody.addEventListener("dragover", function (event) {
      if (!draggedRow) {
        return;
      }

      const targetRow = event.target.closest("tr.nav-sort-row");
      if (!targetRow || targetRow === draggedRow) {
        return;
      }

      event.preventDefault();
      const targetRect = targetRow.getBoundingClientRect();
      const shouldInsertBefore = event.clientY < targetRect.top + targetRect.height / 2;
      tableBody.insertBefore(draggedRow, shouldInsertBefore ? targetRow : targetRow.nextSibling);
    });

    tableBody.addEventListener("drop", function (event) {
      if (draggedRow) {
        event.preventDefault();
      }
    });

    tableBody.addEventListener("dragend", async function () {
      if (!draggedRow) {
        return;
      }

      draggedRow.classList.remove("is-dragging");
      const currentOrder = Array.from(tableBody.querySelectorAll("tr[data-object-id]"))
        .map((row) => row.dataset.objectId)
        .join(",");
      draggedRow = null;

      if (currentOrder === originalOrder) {
        return;
      }

      try {
        await persistOrder(tableBody);
      } finally {
        window.location.reload();
      }
    });
  });
})();

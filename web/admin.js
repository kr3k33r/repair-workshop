const $ = (id) => document.getElementById(id),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
    );
let rows = [],
  statuses = {};
async function load() {
  try {
    const response = await fetch("/api/requests");
    const data = await response.json();
    if (!response.ok) throw Error(data.error);
    rows = data.requests;
    statuses = data.statuses;
    render();
    $("error").textContent = "";
  } catch (e) {
    $("error").textContent = e.message;
  }
}
function render() {
  const filtered = rows.filter(
    (r) => $("filter").value === "all" || r.status === $("filter").value,
  );
  $("summary").textContent =
    `Всего: ${rows.length} · Новых: ${rows.filter((r) => r.status === "new").length} · В работе: ${rows.filter((r) => r.status === "progress").length}`;
  $("requests").innerHTML =
    filtered
      .map(
        (r) =>
          `<article class="request-card"><small>${esc(r.id)} · ${new Date(r.created).toLocaleString("ru-RU")}</small><h3>${esc(r.device_label)}</h3><p class="muted">${esc(r.issue_label)} · ${r.low}–${r.high} ₽</p><p>${esc(r.description)}</p><p><strong>${esc(r.name)}</strong><br>${esc(r.contact)}</p><p class="muted">Когда: ${esc(r.preferred)}</p><label>Статус<select data-id="${esc(r.id)}">${Object.entries(
            statuses,
          )
            .map(
              ([key, label]) =>
                `<option value="${key}"${r.status === key ? " selected" : ""}>${label}</option>`,
            )
            .join("")}</select></label></article>`,
      )
      .join("") ||
    '<div class="empty-state">Заявок с таким статусом пока нет. Оставьте тестовое обращение на сайте.</div>';
  $("requests")
    .querySelectorAll("select")
    .forEach(
      (select) =>
        (select.onchange = async () => {
          select.disabled = true;
          try {
            const response = await fetch("/api/status", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: select.dataset.id, status: select.value }),
            });
            const data = await response.json();
            if (!response.ok) throw Error(data.error);
            await load();
          } catch (e) {
            $("error").textContent = e.message;
            render();
          }
        }),
    );
}
$("filter").onchange = render;
$("refresh").onclick = load;
load();

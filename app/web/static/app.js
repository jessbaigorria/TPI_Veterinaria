// VetRed – JS mínimo (sin build): toasts, confirmaciones, selects dependientes y filtros.
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".toast").forEach((t) => new bootstrap.Toast(t, { delay: 5000 }).show());

  // Confirmación antes de acciones irreversibles: modal de Bootstrap (Aceptar / Cancelar).
  const modalEl = document.getElementById("modal-confirmar");
  const modal = modalEl ? new bootstrap.Modal(modalEl) : null;
  let formPendiente = null;
  document.querySelectorAll("form[data-confirm]").forEach((f) =>
    f.addEventListener("submit", (e) => {
      if (!modal || f.dataset.confirmado === "1") return;
      if (!f.checkValidity()) return;
      e.preventDefault();
      formPendiente = f;
      document.getElementById("modal-confirmar-texto").textContent = f.dataset.confirm;
      document.getElementById("modal-confirmar-detalle").textContent = f.dataset.confirmDetalle || "";
      modal.show();
    }));
  document.getElementById("modal-confirmar-aceptar")?.addEventListener("click", () => {
    if (!formPendiente) return;
    formPendiente.dataset.confirmado = "1";
    modal.hide();
    formPendiente.requestSubmit ? formPendiente.requestSubmit() : formPendiente.submit();
  });

  // Buscador dentro de un <select> (desplegable con buscador).
  document.querySelectorAll("[data-filtra]").forEach((input) => {
    const select = document.getElementById(input.dataset.filtra);
    input.addEventListener("input", () => {
      const q = input.value.toLowerCase();
      let primero = null;
      [...select.options].forEach((o) => {
        const ok = !o.value || o.text.toLowerCase().includes(q);
        o.hidden = !ok;
        if (ok && o.value && !primero) primero = o;
      });
      if (primero && select.selectedOptions[0]?.hidden) { select.value = primero.value; select.dispatchEvent(new Event("change")); }
    });
  });

  // Titular → mascotas (carga por API) con aviso de vacunas pendientes.
  document.querySelectorAll("[data-mascotas-de]").forEach((selMascota) => {
    const selTitular = document.getElementById(selMascota.dataset.mascotasDe);
    const aviso = document.getElementById(selMascota.dataset.aviso || "");
    const elegida = selMascota.dataset.seleccionada;
    const cargar = async () => {
      selMascota.innerHTML = '<option value="">— Elegí la mascota —</option>';
      if (aviso) aviso.innerHTML = "";
      if (!selTitular.value) return;
      const r = await fetch(`/api/titulares/${selTitular.value}/mascotas`);
      const datos = await r.json();
      datos.forEach((m) => {
        const o = new Option(`${m.nombre} (${m.especie})` + (m.pendientes.length ? " · vacunas pendientes" : ""), m.id);
        o.dataset.pendientes = m.pendientes.join(", ");
        selMascota.add(o);
      });
      if (elegida) selMascota.value = elegida;
      selMascota.dispatchEvent(new Event("change"));
    };
    selMascota.addEventListener("change", () => {
      if (!aviso) return;
      const o = selMascota.selectedOptions[0];
      aviso.innerHTML = o && o.dataset.pendientes
        ? `<div class="alert alert-warning py-2 mb-0"><i class="bi bi-exclamation-triangle"></i> Vacunas pendientes: <b>${o.dataset.pendientes}</b>. Una CONSULTA o CONTROL será bloqueada; podés registrar URGENCIA o VACUNACIÓN.</div>`
        : "";
    });
    selTitular.addEventListener("change", cargar);
    if (selTitular.value) cargar();
  });

  // Mostrar/ocultar bloques según un control (data-muestra-si="idControl:valor").
  const actualizar = () => document.querySelectorAll("[data-muestra-si]").forEach((bloque) => {
    const [id, valor] = bloque.dataset.muestraSi.split(":");
    const ctrl = document.getElementById(id);
    if (!ctrl) return;
    const actual = ctrl.type === "checkbox" ? (ctrl.checked ? "1" : "0") : ctrl.value;
    const visible = valor.split("|").includes(actual);
    bloque.classList.toggle("d-none", !visible);
    bloque.querySelectorAll("input,select,textarea").forEach((el) => {
      if (el.dataset.requerido) el.required = visible;
    });
  });
  document.querySelectorAll("input,select").forEach((el) => el.addEventListener("change", actualizar));
  actualizar();

  // Gráficos de reportes (Chart.js).
  document.querySelectorAll("canvas[data-grafico]").forEach((c) => {
    try { new Chart(c, JSON.parse(c.dataset.grafico)); } catch (e) { console.error(e); }
  });
});

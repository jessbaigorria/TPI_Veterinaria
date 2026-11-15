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

  // Combobox con búsqueda (Tom Select) en TODOS los selectores de la app: se abre al hacer clic,
  // filtra mientras se escribe (la lista queda abierta) y se elige con clic o Enter.
  const crearCombo = (sel) => {
    if (sel.tomselect) return sel.tomselect;
    const vacia = sel.querySelector('option[value=""]');
    // En los obligatorios la opción vacía es solo el texto de ayuda; en los filtros ("Todos los …") se puede elegir.
    const opciones = {
      allowEmptyOption: !sel.required, maxOptions: null, create: false, dropdownParent: "body",
      openOnFocus: true, closeAfterSelect: true, selectOnTab: true, searchField: ["text"],
      plugins: ["dropdown_input"],
      render: { no_results: () => '<div class="no-results text-muted px-3 py-2">Sin resultados</div>' },
    };
    if (sel.required && vacia) opciones.placeholder = vacia.textContent.trim();
    const ts = new TomSelect(sel, opciones);
    // Texto del cuadro de búsqueda dentro de la lista desplegada.
    const buscar = sel.dataset.buscar || "Escribí para buscar";
    if (ts.control_input) ts.control_input.placeholder = buscar;
    return ts;
  };
  if (window.TomSelect) document.querySelectorAll("select.form-select").forEach(crearCombo);

  // Titular → mascotas activas del titular (carga por API), con aviso de vacunas pendientes.
  document.querySelectorAll("[data-mascotas-de]").forEach((selMascota) => {
    const selTitular = document.getElementById(selMascota.dataset.mascotasDe);
    const aviso = document.getElementById(selMascota.dataset.aviso || "");
    const placeholder = selMascota.dataset.placeholder || "— Elegí la mascota —";
    let elegida = selMascota.dataset.seleccionada;
    const pendientes = {};
    const ts = selMascota.tomselect;
    const mostrarAviso = () => {
      if (!aviso) return;
      const p = pendientes[selMascota.value];
      aviso.innerHTML = p
        ? `<div class="alert alert-warning py-2 mb-0"><i class="bi bi-exclamation-triangle"></i> Vacunas pendientes: <b>${p}</b>. Para una consulta o un control primero hay que aplicarlas; se puede atender una urgencia o una vacunación.</div>`
        : "";
    };
    const cargar = async () => {
      if (ts) { ts.clear(true); ts.clearOptions(); }
      else selMascota.innerHTML = `<option value="">${placeholder}</option>`;
      if (aviso) aviso.innerHTML = "";
      if (!selTitular.value) return;
      const datos = await (await fetch(`/api/titulares/${selTitular.value}/mascotas`)).json();
      datos.forEach((m) => {
        const texto = `${m.nombre} (${m.especie})` + (m.pendientes.length ? " · vacunas pendientes" : "");
        pendientes[m.id] = m.pendientes.join(", ");
        if (ts) ts.addOption({ value: String(m.id), text: texto }); else selMascota.add(new Option(texto, m.id));
      });
      if (ts) ts.refreshOptions(false);
      if (elegida) { ts ? ts.setValue(String(elegida)) : (selMascota.value = elegida); elegida = null; }
      if (ts) ts.close();
      mostrarAviso();
    };
    selMascota.addEventListener("change", mostrarAviso);
    selTitular.addEventListener("change", cargar);
    cargar();
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

  // Rango de fechas de los filtros: «Hasta» no puede ser anterior a «Desde».
  document.querySelectorAll("form").forEach((f) => {
    const desde = f.querySelector("input[type=date][name=desde]"), hasta = f.querySelector("input[type=date][name=hasta]");
    if (!desde || !hasta) return;
    const ajustar = () => { hasta.min = desde.value || ""; if (desde.value && hasta.value && hasta.value < desde.value) hasta.value = desde.value; };
    desde.addEventListener("change", ajustar); ajustar();
  });

  const aMin = (t) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
  const aHora = (n) => `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;
  const CIERRE = 19 * 60, APERTURA = 8 * 60;

  // Reservar turno: fin autocompletado (inicio + duración máxima del tipo), sin pasar de las 19:00;
  // si la fecha es hoy, el inicio tiene que ser posterior a la hora actual.
  const fTurno = document.querySelector("form[data-horario-turno]");
  if (fTurno) {
    const dur = JSON.parse(fTurno.dataset.duraciones);
    const fecha = fTurno.querySelector("[name=fecha]"), ini = fTurno.querySelector("[name=hora_inicio]");
    const fin = fTurno.querySelector("[name=hora_fin]"), tipo = fTurno.querySelector("[name=tipo]");
    const ayuda = fTurno.querySelector("[data-ayuda-duracion]");
    const ahora = Number(fTurno.dataset.ahoraMin);
    const recalcular = (autocompletar) => {
      let minimo = APERTURA;
      if (fecha.value === fTurno.dataset.hoy) minimo = Math.max(minimo, Math.ceil((ahora + 1) / 5) * 5);
      ini.min = aHora(Math.min(minimo, CIERRE - 5));
      const d = dur[tipo.value] || 30;
      if (ayuda) ayuda.textContent = `Máximo ${d} minutos`;
      if (!ini.value) return;
      const i = aMin(ini.value), tope = Math.min(i + d, CIERRE);
      fin.min = aHora(Math.min(i + 5, CIERRE)); fin.max = aHora(tope);
      if (autocompletar || !fin.value || aMin(fin.value) > tope || aMin(fin.value) <= i) fin.value = aHora(tope);
    };
    ini.addEventListener("change", () => recalcular(true));
    tipo.addEventListener("change", () => recalcular(true));
    fecha.addEventListener("change", () => recalcular(false));
    recalcular(!fin.value);
  }

  // Atención sin turno: duración autocompletada con el máximo del tipo (se puede acortar, no alargar).
  const fSinTurno = document.querySelector("form[data-horario-sin-turno]");
  if (fSinTurno) {
    const dur = JSON.parse(fSinTurno.dataset.duraciones);
    const tipo = fSinTurno.querySelector("[name=tipo]"), duracion = fSinTurno.querySelector("[name=duracion]");
    const ayuda = fSinTurno.querySelector("[data-ayuda-duracion]");
    const recalcular = (autocompletar) => {
      const d = dur[tipo.value] || 30;
      duracion.max = d;
      if (ayuda) ayuda.textContent = `Máximo ${d} minutos`;
      if (autocompletar || !duracion.value || Number(duracion.value) > d) duracion.value = d;
    };
    tipo.addEventListener("change", () => recalcular(true));
    recalcular(!duracion.value);
  }

  // Registrar atención: se usa la mascota elegida o, si se completa el nombre, la mascota nueva.
  const fNueva = document.querySelector("form[data-mascota-nueva]");
  if (fNueva) {
    const nombre = fNueva.querySelector("[name=nm_nombre]"), mascota = fNueva.querySelector("[name=mascota_id]");
    const requeridosNueva = fNueva.querySelectorAll("input[data-nueva], select[data-nueva]");
    const ajustar = () => {
      const nueva = nombre.value.trim() !== "";
      mascota.required = !nueva;
      requeridosNueva.forEach((el) => { el.required = nueva; });
    };
    nombre.addEventListener("input", ajustar); ajustar();
  }

  // DNI con máscara ## ### ### mientras se escribe (solo dígitos; 7 dígitos → # ### ### al salir del campo).
  const formatoDni = (d, final) => {
    if (final && d.length === 7) return `${d[0]} ${d.slice(1, 4)} ${d.slice(4)}`;
    return [d.slice(0, 2), d.slice(2, 5), d.slice(5, 8)].filter(Boolean).join(" ");
  };
  document.querySelectorAll("[data-mascara-dni]").forEach((el) => {
    el.addEventListener("input", () => { el.value = formatoDni(el.value.replace(/\D/g, "").slice(0, 8), false); });
    el.addEventListener("blur", () => { el.value = formatoDni(el.value.replace(/\D/g, "").slice(0, 8), true); });
    el.value = formatoDni(el.value.replace(/\D/g, ""), true);
  });
  document.querySelectorAll("[data-solo-numeros]").forEach((el) =>
    el.addEventListener("input", () => { el.value = el.value.replace(/\D/g, ""); }));

  // Gráficos de reportes (Chart.js).
  document.querySelectorAll("canvas[data-grafico]").forEach((c) => {
    try { new Chart(c, JSON.parse(c.dataset.grafico)); } catch (e) { console.error(e); }
  });
});

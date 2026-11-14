# TPI---Veterinaria-
Trabajo Practico Integrador de Desarrollo de Aplicaciones con Objetos - Grupo 30

# VetRed – Red de Clínicas Veterinarias y Derivación de Laboratorio

**TP Integrador 2026 · DAO · Tema 2 · Grupo 30**
95028 Alvaretto Caterina · 85621 Alvarez Castillo Franco · 401824 Baigorria Jesica · 98118 Blady Octavio Agustín · 96095 Nasimbera Fabrizio

Sistema web que integra la atención clínica de una red de veterinarias con la derivación de muestras a un
laboratorio central, manteniendo la **cadena de custodia** y la **trazabilidad inmutable** de cada muestra
(extracción → empaquetado → tránsito → recepción → análisis o rechazo). Incluye el proceso opcional
**derivaciones para cirugías de alta complejidad**.

- Patrones de diseño: **State** (ciclo de vida de la muestra y del remito) y **Observer** (historial + estado de la orden).
- Los 7 procesos obligatorios, el opcional de cirugía, las 5 validaciones (+ la de cirugía) y 5 reportes con gráfico, tabla y CSV.
- Dos portales sobre los mismos datos: **Portal Clínica** (barra verde azulada) y **Portal Laboratorio** (barra violeta).

---

## 1. Instalación y ejecución

Requisitos: **Python 3.12** (con `pip`). No hace falta Node ni ninguna herramienta de build: el frontend usa
Bootstrap 5, Bootstrap Icons y Chart.js desde CDN (se necesita conexión a internet para verlos con estilo).

**Windows**

```bat
run.bat
```

**Linux / macOS**

```bash
./run.sh
```

Los scripts crean el entorno virtual `.venv`, instalan `requirements.txt`, cargan el seed (solo si la base está
vacía) y levantan la app en **http://localhost:8000**.

Para regenerar la base de datos de prueba (fechas relativas al día de hoy):

```bash
./run.sh --reset
```

(en Windows: `run.bat --reset`). La base es un archivo SQLite `veterinaria.db` en la raíz del proyecto
(no se versiona). También se puede indicar otra con la variable `VETERINARIA_DB_URL`.

**Manual** (equivalente a los scripts):

```bash
python3.12 -m venv .venv
```

```bash
source .venv/bin/activate      # Windows: .venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

```bash
python -m app.seed
```

```bash
uvicorn app.main:app --reload
```

### Tests

```bash
pytest
```

Corre ~130 tests sobre SQLite en memoria: State, Observer, inmutabilidad (3 capas), validaciones, coordinación
remito ↔ muestras ↔ precinto, facturación, reportes con números esperados, seed, smoke test de todas las páginas
de ambos portales y el **escenario de demo completo por HTTP** (`tests/test_demo.py`).

### Ingreso

No hay contraseñas. En `/` se elige el portal:

- **Entrar como Clínica** → clínica + usuario (un profesional de esa clínica o “Recepción”).
- **Entrar como Laboratorio** → laboratorio + nombre del operador.

El usuario elegido queda registrado en toda la auditoría (historial de la muestra, armado del remito, precinto,
recepción, resultados, consentimiento). El botón **Cambiar** de la barra superior vuelve a esta pantalla.

---

## 2. Arquitectura

```
UI (FastAPI + Jinja2)  →  services (casos de uso, transacción)  →  domain (entidades + State + Observer)
                                     ↘ repositories (historial solo-inserción, numerador) ↙
                                              SQLite (SQLAlchemy 2.x)
```

- **Modelo de dominio rico:** las clases SQLAlchemy son las entidades del diagrama y contienen las reglas.
  State y Observer son Python puro.
- **Servicios:** un servicio por proceso de negocio. Cada caso de uso corre en una transacción
  (`app/services/base.py::transaccional`): commit al final, rollback ante cualquier error.
- **UI:** las rutas solo traducen formularios y llaman a los servicios; **nunca** cambian estados ni deciden
  transiciones. Los botones se muestran según lo que el dominio informa (`acciones()`, `transiciones_posibles()`).
- **Errores de negocio:** todas las excepciones heredan de `VeterinariaError`; se capturan en **un solo lugar**
  (`app/main.py::manejar_error_negocio`) y se muestran en un aviso rojo, conservando lo cargado en el formulario.

```
app/
├── main.py                  # FastAPI, sesión, routers y manejo global de VeterinariaError
├── db.py                    # engine, sesión, init_db con triggers de inmutabilidad
├── seed.py                  # datos de prueba (60 días) creados a través de los servicios
├── domain/
│   ├── enums.py, excepciones.py, reloj.py (reloj inyectable), base.py
│   ├── personas.py          # Titular, Mascota, HistoriaClinica, Vacuna, AplicacionVacuna
│   ├── atencion.py          # Clinica, Profesional, AtencionClinica, DerivacionCirugia
│   ├── laboratorio.py       # OrdenDerivacion, TipoAnalisis, MuestraBiologica, HistorialEstadoMuestra, ResultadoAnalisis, Laboratorio
│   ├── transporte.py        # Contenedor, RemitoBiologico, Precinto, Envio, RecepcionRemito
│   ├── facturacion.py       # Factura, ItemFactura
│   ├── estados/             # PATRÓN STATE (estado_muestra.py, estado_remito.py)
│   └── observadores/        # PATRÓN OBSERVER (observadores_muestra.py)
├── repositories/            # Repositorio genérico, HistorialRepository (solo agregar/listar), Numerador
├── services/                # clientes, mascotas, atenciones, derivaciones, empaquetado, envios, recepcion,
│                            # resultados, facturacion, cirugias, catalogos, tableros (KPIs), fabrica_observadores
├── reportes/                # comun.py + r1..r5
└── web/
    ├── routers/             # comunes.py, portal_clinica.py, portal_laboratorio.py, reportes_web.py
    ├── templates/           # base.html, clinica/*, laboratorio/*, componentes/* (badges, línea de tiempo, reporte)
    └── static/              # estilos.css, app.js
tests/                       # pytest
docs/                        # consigna, diagrama, alcances, context.md, DECISIONES.md, TRAZABILIDAD.md
```

---

## 3. Dónde está cada patrón

### State — ciclo de vida de la muestra

| Archivo | Clase | Rol |
|---|---|---|
| `app/domain/estados/estado_muestra.py` | `EstadoMuestra` | Base abstracta: **todas** las transiciones lanzan `TransicionInvalidaError` |
| | `Extraida` | redefine `empaquetar` |
| | `Empaquetada` | redefine `despachar` |
| | `EnTransito` | redefine `recibir` y `rechazar` |
| | `Recibida` | redefine `analizar` (→ Analizada al completar los resultados) |
| | `Analizada` | final (`es_final() = True`) |
| | `Rechazada` | final; `analizar` lanza `MuestraRechazadaError` |
| `app/domain/laboratorio.py` | `MuestraBiologica` | Contexto: `empaquetar/despachar/recibir/rechazar/registrar_resultado` **solo delegan** en `self._estado`; `_cambiar_estado` es el único lugar donde cambia el estado; `@orm.reconstructor _rehidratar_estado` |

### State — ciclo de vida del remito

| Archivo | Clase | Rol |
|---|---|---|
| `app/domain/estados/estado_remito.py` | `EstadoRemito` | Base abstracta (todo inválido) |
| | `RemitoArmado` | `agregar_muestra`, `cerrar` (precinto), `despachar` (muestras → En tránsito) |
| | `RemitoDespachado` | `iniciar_transito` |
| | `RemitoEnTransito` | `recibir` → `RemitoRecibido` (muestras Recibidas) o `RemitoRecibidoConObservaciones` (muestras Rechazadas) |
| | `RemitoRecibido`, `RemitoRecibidoConObservaciones` | finales |
| `app/domain/transporte.py` | `RemitoBiologico` | Contexto; el estado se persiste como string y se rehidrata con `@orm.reconstructor` |

### Observer — trazabilidad

| Archivo | Clase | Rol |
|---|---|---|
| `app/domain/observadores/observadores_muestra.py` | `ObservadorMuestra` | «interface» `actualizar(muestra, anterior, nuevo, motivo, usuario)` |
| | `RegistroHistorial` | crea el `HistorialEstadoMuestra` (único que escribe historial) |
| | `ActualizadorEstadoOrden` | `orden.actualizar_estado()` → EN_PROCESO / COMPLETADA |
| `app/domain/laboratorio.py` | `MuestraBiologica.agregar_observador`, `_notificar` | sujeto: notifica dentro de `_cambiar_estado` |
| `app/services/fabrica_observadores.py` | `adjuntar_observadores` | **único lugar** donde se adjuntan (eventos `init` y `load` de la muestra) |

### Trazabilidad inmutable (3 capas)

1. **Dominio:** `HistorialEstadoMuestraFila` no admite modificaciones; `muestra.historial()` devuelve una `tuple` de `HistorialEstadoMuestra` (`dataclass(frozen=True)`).
2. **Repositorio:** `app/repositories/historial.py::HistorialRepository` solo tiene `agregar()` y `listar_por_muestra()`; listeners `before_update`/`before_delete` lanzan `HistorialInmutableError`.
3. **Base de datos:** triggers `historial_no_update` y `historial_no_delete` (`RAISE(ABORT, …)`) creados en `app/db.py::init_db`.

Toda muestra nace con el registro “— → Extraída” (motivo “Extracción en consulta”).

---

## 4. Validaciones de negocio

| Validación | Excepción | Dónde |
|---|---|---|
| Toda mascota tiene un titular responsable | `MascotaSinTitularError` | `Mascota.__init__`, `Mascota.cambiar_titular` |
| Precinto roto → muestras Rechazadas, sin procesar | `MuestraRechazadaError` | `RecepcionRemito.procesar` → `RemitoEnTransito.recibir` → `EnTransito.rechazar`; `Rechazada.analizar` |
| Trazabilidad inmutable | `HistorialInmutableError` / trigger | ver sección 3 |
| Sin superposición de turnos | `TurnoSuperpuestoError` | `Profesional.esta_disponible` + `AtencionClinica.se_superpone_con` (ignora canceladas) |
| Vacunas obligatorias al registrar la atención | `VacunasPendientesError` | `AtencionClinica.iniciar` → `verificar_vacunas_obligatorias` → `HistoriaClinica.vacunas_pendientes` (CONSULTA/CONTROL bloquean; URGENCIA advierte; VACUNACIÓN resuelve) |
| Cirugía: destino de alta complejidad, consentimiento, ASA ≥ III con estudios | `DerivacionCirugiaError` | `DerivacionCirugia.__init__`, `DerivacionCirugia.programar` |

Además: temperatura fuera del rango del contenedor (despacho o recepción), capacidad del contenedor, tipo de muestra
compatible con los análisis, no facturar dos veces, no cobrar análisis de muestras rechazadas, transiciones inválidas
de muestra/remito (`TransicionInvalidaError`).

---

## 5. Pantallas

**Portal Clínica** (`/clinica`)

| Sección | Qué se hace |
|---|---|
| Inicio | KPIs: turnos de hoy, atenciones en curso, muestras sin empaquetar, remitos armados, remitos en camino, **rechazadas en 7 días (alerta roja)**, resultados nuevos, cirugías pendientes; turnos del día, resultados recientes, últimos remitos. |
| Agenda | Grilla del día por profesional (franjas de 30 min), reservar turno (titular → mascota → profesional → horario → tipo), iniciar y cancelar. |
| Atenciones | Registrar atención sin turno con los **3 casos** del grupo (titular presente / “+ Nueva mascota” / no asiste el titular → responsable presente); control de vacunas; finalizar (diagnóstico, observaciones, peso, importe, vacunas aplicadas si es VACUNACIÓN); botones **Emitir orden de laboratorio · Derivar a cirugía · Emitir comprobante**. |
| Clientes | ABM de titulares con búsqueda por DNI/nombre, ficha con mascotas y facturas, baja lógica. |
| Mascotas | ABM (siempre con titular). Ficha = historia clínica con pestañas Resumen · Atenciones · Vacunas · Laboratorio (órdenes, muestras con línea de tiempo y resultados) · Cirugías · Facturas. |
| Órdenes lab | Lista y detalle: análisis, indicaciones, muestras con badge y línea de tiempo; registrar muestra (nace Extraída); anular. |
| Envíos | Armar remito en 3 pasos (laboratorio + contenedor → tildar muestras → cerrar con precinto y temperatura), despachar, confirmar retiro; resultado de la recepción. |
| Cirugías | Enviadas y (si la clínica es de alta complejidad) Recibidas: aceptar, rechazar, consentimiento, estudios, programar, registrar cirugía, cancelar, facturar. |
| Facturación | Pendiente de facturar (atenciones, órdenes completadas, cirugías realizadas), comprobantes, pago y anulación. |
| Reportes | R1–R5 con filtros, gráfico, tabla y CSV. |
| Catálogos | Clínicas, profesionales, laboratorios, tipos de análisis, vacunas (esquema) y contenedores (mantenimiento/habilitar). |

**Portal Laboratorio** (`/laboratorio`)

| Sección | Qué se hace |
|---|---|
| Inicio | KPIs: remitos en camino, muestras por analizar, analizadas hoy, rechazadas en 7 días, tránsito promedio del mes. |
| Recepción | Bandeja de remitos En tránsito (y en gris los despachados esperando retiro). **Recibir**: código de precinto leído, ¿precinto íntegro? Sí/No, temperatura, observaciones → pantalla ACEPTADA (verde) o RECHAZADA (roja, con motivo) y la lista de muestras. |
| Muestras a analizar | Cola de muestras Recibidas (URGENTE primero). Carga de resultados: un bloque por análisis compatible → Analizada. |
| Trazabilidad | Búsqueda por código de muestra o remito: línea de tiempo + cadena de custodia (quién extrajo, armó, precintó, transportó, recibió y analizó). |
| Recepciones | Historial de recepciones aceptadas y rechazadas con motivo. |
| Reportes | R2 y R3 del laboratorio. |

Componentes comunes: badges de estado con colores fijos (Extraída gris · Empaquetada azul · En tránsito naranja ·
Recibida celeste · Analizada verde · Rechazada rojo; remito Armado gris · Despachado azul · En tránsito naranja ·
Recibido verde · Recibido con observaciones rojo) y la **línea de tiempo** del historial. Fechas `dd/mm/aaaa HH:MM`,
montos `$ 12.500,00`.

---

## 6. Datos de prueba

`python -m app.seed` crea, **a través de los servicios** y con el reloj inyectable, 60 días de historia:
Clínica Centro, Clínica Norte y Hospital Veterinario Sur (alta complejidad); Laboratorio Central de Diagnóstico
Veterinario; 8 profesionales; esquema de vacunas de perro y gato (+ Leptospirosis no obligatoria); 7 tipos de
análisis; 7 contenedores (NOR‑02 en mantenimiento); 11 titulares y 17 mascotas; ~80 atenciones; 14 órdenes;
12 remitos en todos los estados (**REM‑000003 con precinto roto** y **REM‑000004 con temperatura fuera de rango**);
resultados; facturas pagadas, pendientes y una anulada; cirugías solicitada, aceptada, programada, realizada,
rechazada y cancelada; y la agenda de hoy.

Mascotas útiles para la demo: **Rocco** (titular Juan García) con vacunas vencidas, **Mía** (Carlos Fernández)
sin triple felina y **Toby** (Martín Herrera), cachorro sin vacunar.

---

## 7. Escenario de demo paso a paso

> Este mismo recorrido está automatizado en `tests/test_demo.py` (corre con `pytest`).

1. **Turnos superpuestos.** Entrar como *Clínica Centro · Laura Pérez*. *Agenda › Reservar turno*: titular García,
   mascota Firulais, profesional Laura Pérez, mañana 14:00 → “Turno reservado”. Reservar otro para **Rocco** con la
   misma profesional a las 14:15 → aviso rojo **TurnoSuperpuestoError**.
2. **Vacunas.** *Atenciones › Registrar atención*: titular García, mascota Rocco (aparece “⚠ vacunas”), tipo
   **Control** → aviso rojo **VacunasPendientesError** con la lista (Antirrábica, Séxtuple). Clic en
   **“Atender ahora como VACUNACIÓN”** → registrar → en la atención, *Finalizar*: las vacunas pendientes vienen
   tildadas; cargar diagnóstico e importe → “Se registraron 2 vacuna(s)”. Registrar de nuevo el **Control** de Rocco
   (con otro horario o con el Dr. Martín Díaz, para no superponer) → ahora pasa.
3. **Mascota sin titular.** *Mascotas › Nueva mascota* dejando “— Sin titular —” → aviso rojo **MascotaSinTitularError**.
4. **Orden y muestra.** En la atención de control: **Emitir orden de laboratorio** → Hemograma completo + Perfil renal →
   en la orden, *Registrar muestra* Sangre 3 ml → badge **Extraída** y línea de tiempo “— → Extraída”.
5. **Remito.** *Envíos › Armar remito*: Laboratorio Central + contenedor CEN‑02 → tildar la muestra (**Empaquetada**) →
   *Cerrar* con el precinto propuesto (PRE‑…) y temperatura 4 → *Despachar* (transportista, llegada estimada;
   muestra **En tránsito**, orden EN PROCESO) → *Confirmar retiro* (remito En tránsito).
6. **Laboratorio.** *Cambiar* → *Entrar como Laboratorio* (operador Gómez). *Recepción* → **Recibir** el remito:
   precinto íntegro **Sí**, 5 °C → **ACEPTADA**, muestra **Recibida** → *Cargar resultados* → **Analizada**.
   En el portal de la clínica la orden quedó **COMPLETADA** sola (Observer).
7. **Precinto roto.** Repetir 4–6 con una orden nueva y el contenedor CEN‑03, pero al recibir marcar **No, roto** →
   **RECHAZADA – Precinto roto**, remito “Recibido con observaciones”, muestra **Rechazada** (no aparece en la cola).
   Desde *Trazabilidad* › la muestra › “Intentar cargar un resultado” → aviso rojo **MuestraRechazadaError**.
8. **Trazabilidad.** *Laboratorio › Trazabilidad*: buscar los dos códigos (M‑…) → línea de tiempo completa con
   fecha, usuario y motivo de cada cambio, y la cadena de custodia. Los registros no se pueden editar ni borrar.
9. **Cirugía de alta complejidad.** En la atención de Rocco: **Derivar a cirugía** → probar destino Clínica Norte →
   **DerivacionCirugiaError**; destino Hospital Veterinario Sur → enviada. *Cambiar* → *Clínica: Hospital Veterinario
   Sur · Diego Ríos* → *Cirugías › Recibidas*: **Aceptar** (cirujano) → *Programar* sin consentimiento →
   **DerivacionCirugiaError** → *Registrar consentimiento* → *Programar* → *Registrar cirugía* (informe) →
   *Emitir comprobante* con el importe.
10. **Facturación y reportes.** Volver a Clínica Centro: *Facturación › Pendiente de facturar* → emitir el comprobante
    de la atención y el de laboratorio (la orden con la muestra rechazada no tiene nada para facturar). Abrir
    *Reportes* R1 a R5 (filtros, gráfico, tabla, **Exportar CSV**).

---

## 8. Documentación del TP

- `docs/tema2.pdf` – consigna oficial.
- `docs/diagrama_clases_v2.drawio` – diagrama de clases (hoja “Diagrama de clases”) y notas del grupo (hoja “opciones”).
- `docs/Presentacion-grupo_30.docx.md` – objetivos y alcances.
- `docs/context.md` – contexto completo usado para el desarrollo.
- `docs/DECISIONES.md` – **desvíos respecto del diagrama** y decisiones tomadas.
- `docs/TRAZABILIDAD.md` – requisito de la consigna → clase/método → pantalla → test.

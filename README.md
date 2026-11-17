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
- Los 7 procesos obligatorios, el opcional de cirugía, las 5 validaciones (+ la de cirugía) y 5 reportes con gráfico, tabla y exportación a PDF.
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

Corre ~300 tests sobre SQLite en memoria: State, Observer, inmutabilidad (3 capas), validaciones, coordinación
remito ↔ muestras ↔ precinto, facturación, reportes con números esperados, seed, smoke test de todas las páginas
de ambos portales y el **escenario de demo completo por HTTP** (`tests/test_demo.py`).

Los tests de **comportamiento de los patrones** están en `test_observer.py` (O1–O10: el observador ve el estado ya
cambiado, una transición fallida o un resultado parcial no notifican, sin duplicados, desacople, pull de la orden,
matriz de `actualizar_estado()`…), `test_state_muestra.py` (S1–S5) y `test_state_remito.py` (R1–R4). Las rondas de
correcciones del grupo se verifican en `test_correcciones_web.py`, `test_correcciones_ronda2.py` y
`test_correcciones_ronda2_web.py`.

### Ingreso

No hay contraseñas. En `/` se elige el portal:

- **Entrar como Clínica** → elegir la clínica.
- **Entrar como Laboratorio** → elegir el laboratorio.

La sede elegida es el usuario de la sesión y queda en la auditoría. Donde importa la persona, el formulario la pide
(solo letras): **Colocado por** al cerrar un remito con precinto, **Recibido por** en la recepción del laboratorio y
**Analista** al cargar resultados. La extracción de la muestra queda a nombre del profesional de la atención.
El botón **Cambiar** de la barra superior pide confirmación (“Se cerrará la sesión”, Sí / No): con **Sí** cierra la
sesión y vuelve a esta pantalla; con **No** sigue en la misma página.

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
├── db.py                    # engine, sesión, init_db con triggers de inmutabilidad (y migración de nombres de estado)
├── seed/                    # datos de prueba (60 días) creados a través de los servicios:
│                            # datos.py (tablas), sembrador.py (operaciones) y un módulo por etapa
├── domain/
│   ├── enums.py, excepciones.py, reloj.py (reloj inyectable), base.py
│   ├── personas.py          # Titular, Mascota, HistoriaClinica, Vacuna, AplicacionVacuna
│   ├── clinica.py           # Clinica, Profesional
│   ├── atencion.py          # AtencionClinica
│   ├── cirugia.py           # DerivacionCirugia (proceso opcional)
│   ├── laboratorio.py       # Laboratorio, TipoAnalisis, OrdenDerivacion
│   ├── muestra.py           # MuestraBiologica, HistorialEstadoMuestra (inmutable), ResultadoAnalisis
│   ├── transporte.py        # Contenedor, RemitoBiologico, Precinto, Envio, RecepcionRemito
│   ├── facturacion.py       # Factura, ItemFactura, ConFacturas (lo común a lo que se factura)
│   ├── estados/             # PATRÓN STATE (estado_muestra.py, estado_remito.py)
│   └── observadores/        # PATRÓN OBSERVER (observadores_muestra.py)
├── repositories/            # Repositorio genérico, HistorialRepository (solo agregar/listar), Numerador
├── services/                # clientes, mascotas, atenciones, derivaciones, empaquetado, envios, recepcion,
│                            # resultados, facturacion, cirugias, catalogos, tableros (KPIs), fabrica_observadores
├── reportes/                # comun.py, pdf.py (exportación con ReportLab) y un módulo por reporte
└── web/
    ├── routers/             # _comun.py (helpers), comunes.py, portal_laboratorio.py, reportes_web.py y
    │                        # portal_clinica/ (un módulo por sección: agenda, atenciones, clientes, …)
    ├── templates/           # base.html, clinica/*, laboratorio/*, componentes/* (badges, línea de tiempo, reporte)
    └── static/              # estilos.css, app.js
tests/                       # pytest: dominio, servicios, web por HTTP, demo y comportamiento de State/Observer
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
| `app/domain/muestra.py` | `MuestraBiologica` | Contexto: `empaquetar/despachar/recibir/rechazar/registrar_resultado` **solo delegan** en `self._estado`; `_cambiar_estado` es el único lugar donde cambia el estado; `@orm.reconstructor _rehidratar_estado` |

### State — ciclo de vida del remito

| Archivo | Clase | Rol |
|---|---|---|
| `app/domain/estados/estado_remito.py` | `EstadoRemito` | Base abstracta (todo inválido). Los nombres de las clases indican el estado, sin el prefijo “Remito” (igual que en la muestra) |
| | `Armado` | `agregar_muestra`, `cerrar` (precinto), `despachar` (muestras → En tránsito) |
| | `Despachado` | `iniciar_transito` |
| | `EnTransito` | `recibir` → `Recibido` (muestras Recibidas) o `RecibidoConObservaciones` (muestras Rechazadas) |
| | `Recibido`, `RecibidoConObservaciones` | finales |
| `app/domain/transporte.py` | `RemitoBiologico` | Contexto; el estado se persiste como string y se rehidrata con `@orm.reconstructor` |

### Observer — trazabilidad

| Archivo | Clase | Rol |
|---|---|---|
| `app/domain/observadores/observadores_muestra.py` | `ObservadorMuestra` | «interface» `actualizar(muestra, anterior, nuevo, motivo, usuario)` |
| | `RegistroHistorial` | crea el `HistorialEstadoMuestra` (único que escribe historial) |
| | `ActualizadorEstadoOrden` | `orden.actualizar_estado()` → EN_PROCESO / COMPLETADA |
| `app/domain/muestra.py` | `MuestraBiologica.agregar_observador`, `_notificar` | sujeto: notifica dentro de `_cambiar_estado` |
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
| Precinto roto → muestras Rechazadas, sin procesar | `MuestraRechazadaError` | `RecepcionRemito.procesar` → `EnTransito.recibir` (remito) → `EnTransito.rechazar` (muestra); `Rechazada.analizar` |
| Trazabilidad inmutable | `HistorialInmutableError` / trigger | ver sección 3 |
| Sin superposición de turnos | `TurnoSuperpuestoError` | `Profesional.esta_disponible` + `AtencionClinica.se_superpone_con` (ignora canceladas) |
| Vacunas obligatorias al registrar la atención | aviso (no bloquea) | `AtencionClinica.iniciar` → `verificar_vacunas_obligatorias` → `HistoriaClinica.vacunas_pendientes` (avisa “Vacunas pendientes: …” y deja constancia en observaciones; VACUNACIÓN las resuelve) |
| Cirugía: destino de alta complejidad, consentimiento, ASA ≥ III con estudios | `DerivacionCirugiaError` | `DerivacionCirugia.__init__`, `DerivacionCirugia.programar` |

Además: temperatura fuera del rango del contenedor (despacho o recepción), capacidad del contenedor, tipo de muestra
compatible con los análisis, no facturar dos veces, no cobrar análisis de muestras rechazadas, transiciones inválidas
de muestra/remito (`TransicionInvalidaError`).

Reglas agregadas en la primera ronda de correcciones del grupo (ver `docs/DECISIONES.md`):

| Regla | Excepción | Dónde |
|---|---|---|
| Horario de atención 08:00–19:00, duración máxima por tipo (30 min consulta/control/vacunación; 60 min cirugía/otro/urgencia), fin > inicio | `DatosInvalidosError` | `AtencionClinica._validar_horario` |
| Turnos solo para más tarde hoy o fechas futuras; no se reservan urgencias | `DatosInvalidosError` | `AtencionClinica.reservar` |
| Atención sin turno solo con fecha y hora actual o pasada | `DatosInvalidosError` | `AtencionClinica.registrar_sin_turno` |
| Importe obligatorio y mayor a 0 al finalizar | `DatosInvalidosError` | `AtencionClinica.finalizar` |
| Órdenes y derivaciones solo con la atención en curso; una atención finalizada no se modifica | `AtencionNoModificableError` | `AtencionClinica.emitir_orden_derivacion`, `derivar_a_cirugia` |
| Titular: todos los datos obligatorios, DNI de 7 u 8 dígitos y único, teléfono de 8 a 15 dígitos, email válido, nombres solo letras | `DatosInvalidosError` | `Titular.actualizar_datos`, `ClientesService` |
| Nombres de personas (responsable presente, recibido por, analista, colocado por): solo letras, mín. 3 | `DatosInvalidosError` | `app/domain/validaciones.py` |
| Rango de fechas de filtros y reportes: «Hasta» ≥ «Desde» (en reportes, las dos obligatorias) | `DatosInvalidosError` | `services/base.py::validar_rango_fechas` |

Reglas de la segunda ronda de correcciones (PDF “Errores y cosas a mejorar”; ver `docs/DECISIONES.md`, sección S2):

| Regla | Excepción | Dónde |
|---|---|---|
| Vacunas pendientes: solo avisan (“Vacunas pendientes: …”), no bloquean atenciones ni turnos | — | `AtencionClinica.verificar_vacunas_obligatorias`, `iniciar` |
| Nombre y raza de la mascota: solo letras y espacios (raza opcional) | `DatosInvalidosError` | `Mascota.validar_nombre`, `Mascota.validar_raza` |
| Mascota elegida **o** mascota nueva, nunca las dos (atención sin turno y reservar turno) | `DatosInvalidosError` | `AtencionesService._mascota_elegida_o_nueva` |
| Baja de una mascota (o de su titular): se cancelan sus turnos reservados y la atención en curso; no se le reservan turnos | `VeterinariaError` | `Mascota.dar_de_baja` → `AtencionClinica.cancelar_por_baja`; `AtencionClinica._validar_participantes` |
| Teléfono y email de clínicas, profesionales y laboratorios (si se cargan): mismo formato que los titulares | `DatosInvalidosError` | `CatalogosService` (campos `tel` / `email`) → `validaciones.telefono`, `validaciones.email` |
| Una clínica de alta complejidad no puede desactivarla al editar (sí se puede habilitar al crear o editar) | `DatosInvalidosError` | `Clinica._validar_alta_complejidad` (`@validates`) |

---

## 5. Pantallas

**Portal Clínica** (`/clinica`)

| Sección | Qué se hace |
|---|---|
| Inicio | KPIs: turnos de hoy, atenciones en curso, muestras sin empaquetar, remitos armados, remitos en camino, **rechazadas en 7 días (alerta roja)**, resultados nuevos, cirugías pendientes; turnos del día, resultados recientes, últimos remitos. |
| Agenda | Grilla del día por profesional (franjas de 30 min), reservar turno (titular → mascota del titular **o** “Nueva mascota” → profesional → horario → tipo; “¿No existe? Crear titular”), iniciar y cancelar. |
| Atenciones | Registrar atención sin turno con los **3 casos** del grupo (titular presente / “Nueva mascota”, solo si no se eligió una / no asiste el titular → responsable presente); aviso de vacunas pendientes (no bloquea); finalizar (diagnóstico, observaciones, peso, importe, vacunas aplicadas si es VACUNACIÓN); botones **Emitir orden de laboratorio · Derivar a cirugía · Emitir comprobante**. |
| Clientes | ABM de titulares con búsqueda por DNI/nombre, ficha con mascotas y facturas, baja lógica (también de sus mascotas, con sus turnos cancelados). |
| Mascotas | ABM (siempre con titular). Ficha = historia clínica con pestañas Resumen · Atenciones · Vacunas · Laboratorio (órdenes, muestras con línea de tiempo y resultados) · Cirugías · Facturas. Baja lógica: cancela los turnos reservados y la atención en curso. |
| Órdenes lab | Lista y detalle: análisis, indicaciones, muestras con badge y línea de tiempo; registrar muestra (nace Extraída); anular. |
| Envíos | Armar remito en 3 pasos (laboratorio + contenedor → tildar muestras → cerrar con precinto y temperatura), despachar, confirmar retiro; resultado de la recepción. |
| Cirugías | Enviadas y (si la clínica es de alta complejidad) Recibidas: aceptar, rechazar, consentimiento, estudios, programar, registrar cirugía, cancelar, facturar. |
| Facturación | Pendiente de facturar (atenciones, órdenes completadas, cirugías realizadas), comprobantes, pago y anulación. |
| Reportes | Atenciones y derivaciones · Muestras rechazadas · Tiempos de tránsito · Facturación por clínica y laboratorio · Vacunas pendientes: filtros, gráfico, tabla y **Exportar PDF**. |
| Gestión | Clínicas, profesionales, laboratorios, tipos de análisis, vacunas (esquema) y contenedores (mantenimiento/habilitar). Teléfono y email con formato validado; la alta complejidad de una clínica, una vez habilitada, queda fija. |

**Portal Laboratorio** (`/laboratorio`)

| Sección | Qué se hace |
|---|---|
| Inicio | KPIs: remitos en camino, muestras por analizar, analizadas hoy, rechazadas en 7 días, tránsito promedio del mes. |
| Recepción | Bandeja de remitos En tránsito (y en gris los despachados esperando retiro). **Recibir**: código de precinto leído, ¿precinto íntegro? Sí/No, temperatura, **Recibido por**, observaciones → pantalla ACEPTADA (verde) o RECHAZADA (roja, con motivo) y la lista de muestras. |
| Muestras a analizar | Cola de muestras Recibidas (URGENTE primero). Carga de resultados: un bloque por análisis compatible → Analizada. |
| Trazabilidad | Búsqueda por código de muestra o remito: línea de tiempo + cadena de custodia (quién extrajo, armó, precintó, transportó, recibió y analizó). |
| Recepciones | Historial de recepciones aceptadas y rechazadas con motivo. |
| Reportes | Muestras rechazadas y Tiempos de tránsito del laboratorio. |

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
sin triple felina y **Toby** (Martín Herrera), cachorro sin vacunar (las tres muestran el aviso de vacunas
pendientes, pero se pueden atender).

Si tenés una `veterinaria.db` creada antes de los últimos cambios, la app actualiza sola los nombres de estado de
los remitos al arrancar. Los teléfonos con guiones del seed anterior (por ejemplo `351-422-1100`) hay que
corregirlos al editar esa clínica o profesional, o regenerar la base con `--reset`.

---

## 7. Escenario de demo paso a paso

> Este mismo recorrido está automatizado en `tests/test_demo.py` (corre con `pytest`).

1. **Turnos superpuestos.** Entrar como *Clínica Centro*. *Agenda › Reservar turno*: titular García, mascota Firulais,
   profesional Laura Pérez, mañana 14:00 (el fin se completa solo: 14:30) → “Turno reservado”. Reservar otro para
   **Rocco** con la misma profesional a las 14:15 → aviso rojo “Laura Pérez ya tiene un turno de 14:00 a 14:30…”.
   (Un turno en el pasado, fuera de 08:00–19:00 o más largo que el máximo del tipo también se rechaza.)
2. **Vacunas.** *Atenciones › Registrar atención*: titular García, mascota Rocco (aparece “Vacunas pendientes:
   Antirrábica, Séxtuple”), tipo **Control**, una hora de hoy ya pasada entre 08:00 y 19:00 → se registra igual (las
   vacunas pendientes no bloquean): aviso amarillo y constancia en *Observaciones*. Registrar otra atención de Rocco,
   tipo **Vacunación** (otro horario) → en la atención, *Finalizar*: las vacunas pendientes vienen tildadas; cargar
   diagnóstico e importe → “Se registraron 2 vacuna(s)”. Al volver a elegir a Rocco ya no aparece el aviso.
3. **Mascota sin titular.** *Mascotas › Nueva mascota* sin elegir titular → aviso rojo “No se puede registrar una
   mascota sin titular responsable”.
4. **Orden y muestra.** En la atención de control **en curso**: **Emitir orden de laboratorio** → Hemograma completo +
   Perfil renal → en la orden, *Registrar muestra* Sangre 3 ml → badge **Extraída** y línea de tiempo “— → Extraída”.
5. **Remito.** *Envíos › Armar remito*: Laboratorio Central + contenedor CEN‑02 → tildar la muestra (**Empaquetada**) →
   *Cerrar* con el precinto propuesto (PRE‑…), temperatura 4 y **Colocado por** → *Despachar* (transportista, llegada
   estimada; muestra **En tránsito**, orden EN PROCESO) → *Confirmar retiro* (remito En tránsito).
6. **Laboratorio.** *Cambiar* → **Sí** → *Entrar como Laboratorio*. *Recepción* → **Recibir** el remito: precinto íntegro **Sí**,
   5 °C, **Recibido por** → **ACEPTADA**, muestra **Recibida** → *Cargar resultados* (con **Analista**) → **Analizada**.
   En el portal de la clínica la orden quedó **COMPLETADA** sola (Observer).
7. **Precinto roto.** Repetir 4–6 con una orden nueva y el contenedor CEN‑03, pero al recibir marcar **No, roto** →
   **RECHAZADA – Precinto roto**, remito “Recibido con observaciones”, muestra **Rechazada** (no aparece en la cola).
   Desde *Trazabilidad* › la muestra › “Ver carga de resultados” → guardar → aviso rojo “La muestra … fue rechazada…
   no se pueden registrar resultados”.
8. **Trazabilidad.** *Laboratorio › Trazabilidad*: buscar los dos códigos (M‑…) → línea de tiempo completa con
   fecha, usuario y motivo de cada cambio, y la cadena de custodia. Los registros no se pueden editar ni borrar.
9. **Cirugía de alta complejidad.** En la atención de Rocco **en curso**: **Derivar a cirugía** → probar destino Clínica
   Norte → aviso “no está habilitada para cirugías de alta complejidad”; destino Hospital Veterinario Sur → enviada.
   *Cambiar* → **Sí** → *Clínica: Hospital Veterinario Sur* → *Cirugías › Recibidas*: **Aceptar** (cirujano) → *Programar* sin
   consentimiento → aviso rojo → *Registrar consentimiento* → *Programar* → *Registrar cirugía* (informe) →
   *Emitir comprobante* con el importe.
10. **Facturación y reportes.** Volver a Clínica Centro: finalizar la atención (importe obligatorio) → *Facturación ›
    Pendiente de facturar* → emitir el comprobante de la atención y el de laboratorio (desaparecen de la lista; la orden
    con la muestra rechazada no tiene nada para facturar). Abrir los cinco *Reportes* (filtros, gráfico, tabla,
    **Exportar PDF**).

---

## 8. Documentación del TP

- `docs/tema2.pdf` – consigna oficial.
- `docs/diagrama_clases_v2.drawio` – diagrama de clases (hoja “Diagrama de clases”) y notas del grupo (hoja “opciones”).
- `docs/Presentacion-grupo_30.docx.md` – objetivos y alcances.
- `docs/context.md` – contexto completo usado para el desarrollo.
- `docs/DECISIONES.md` – **desvíos respecto del diagrama** y decisiones tomadas (incluye las dos rondas de
  correcciones del grupo y la refactorización del backend).
- `docs/TRAZABILIDAD.md` – requisito de la consigna → clase/método → pantalla → test.
- `docs/PRUEBAS_MANUALES.md` – checklist de pruebas manuales de todos los flujos.

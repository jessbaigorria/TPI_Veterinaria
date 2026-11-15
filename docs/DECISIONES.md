# Decisiones y desvíos respecto del diagrama de clases

Este documento registra **todo lo que se agregó o cambió** respecto de `docs/diagrama_clases_v2.drawio`
(hoja “Diagrama de clases”) y las decisiones tomadas donde la consigna, el diagrama, el documento de
alcances o `context.md` no definían algo. Sirve para que el grupo actualice el diagrama.

Prioridad aplicada cuando algo chocaba: consigna → diagrama de clases → documento de alcances → `context.md`.

---

## 0. Repositorio y entorno

| # | Decisión | Motivo |
|---|---|---|
| 0.1 | Los archivos de referencia están en `docs/` (no en `docs/consigna/`) y el documento de alcances está como `docs/Presentacion-grupo_30.docx.md`. **No se movieron ni modificaron.** | Así estaban en la rama `nasimbera`. |
| 0.2 | El proyecto se creó en la **raíz del repo** (`app/`, `tests/`, `run.sh`, …). | La raíz solo tenía `README.md` y `docs/`; no había código previo del grupo. El `README.md` original (2 líneas) se amplió conservando su título. |
| 0.3 | Dependencias fijadas a versiones probadas (`requirements.txt`): FastAPI 0.163, SQLAlchemy 2.1, Starlette 1.10, Jinja2 3.1, pytest 9. | Reproducibilidad en Windows/Linux con Python 3.12. |
| 0.4 | Sin HTMX: un JS mínimo (`app/web/static/app.js`) hace el `fetch` de mascotas del titular, filtros de selects, toasts y gráficos. | Más simple que sumar otra librería; sigue sin build. |
| 0.5 | Sesión con `SessionMiddleware` de Starlette (cookie firmada). Secreto por defecto en código; se puede cambiar con la variable `VETERINARIA_SECRET`. | Es un TP sin contraseñas. |

## 1. Convenciones de mapeo del diagrama a Python/SQLAlchemy

| # | Decisión |
|---|---|
| 1.1 | Los atributos privados (`-`) del diagrama se mapean como **columnas ORM con el mismo nombre** y sin guion bajo (`titular.dni`, `muestra.codigo`). Python no tiene privacidad real y así coinciden los nombres con el diagrama. |
| 1.2 | Cada entidad tiene `id` (PK) y las asociaciones se implementan como `relationship` + FK (las FK no figuran en el diagrama, como indica `context.md`). |
| 1.3 | Métodos de visibilidad paquete (`~`) y privados (`-`) usan guion bajo: `~cambiar_estado` → `MuestraBiologica._cambiar_estado`, `-notificar` → `_notificar`. Solo los usan las clases de estado. |
| 1.4 | `MuestraBiologica.estado` / `RemitoBiologico.estado` (tipo `EstadoMuestra`/`EstadoRemito`): la **columna** `estado` (string, nombre de la clase de estado, p. ej. `"EnTransito"`) se mapea al atributo `estado_codigo`; la **propiedad** `estado` devuelve el objeto State (`self._estado`), rehidratado con `@orm.reconstructor` (y con un listener `refresh`). El registro `{nombre: clase}` vive en `EstadoMuestra.desde_nombre()` / `EstadoRemito.desde_nombre()` y no decide comportamiento. |
| 1.5 | `HistorialEstadoMuestra` «inmutable» se implementa con **dos clases**: `HistorialEstadoMuestraFila` (ORM, tabla `historial_estado_muestra`, no admite `setattr`/`delattr` después de construida) y `HistorialEstadoMuestra` (`@dataclass(frozen=True)`), que es lo que devuelve `muestra.historial()` como `tuple`. |
| 1.6 | Montos (`Decimal`) se guardan como **centavos enteros** (`app/domain/base.py::Dinero`) para que `SUM()` en SQLite sea exacto en los reportes. |
| 1.7 | Los enums heredan de `str` y tienen la propiedad `etiqueta` (texto para la UI). `RiesgoAnestesico` agrega `nivel` (1–5). |
| 1.8 | Numeración automática `HC-`, `ORD-`, `M-`, `REM-`, `PRE-`, `FAC-`, `CIR-` en la tabla auxiliar `secuencia` (`app/repositories/numerador.py`, upsert atómico en la transacción del caso de uso). Los métodos de dominio que crean objetos numerados reciben un parámetro opcional `numero=`/`codigo=` que completa el servicio. |

## 2. Patrón State

| # | Agregado / cambio | Motivo |
|---|---|---|
| 2.1 | `EstadoRemito.agregar_muestra(r, m, usuario)` y `EstadoRemito.cerrar(r, precinto)` (base = inválido) redefinidos solo en `RemitoArmado`. | Pedido explícito de `context.md` 5.2: agregar muestras y cerrar solo es válido en Armado. **Falta en el diagrama.** |
| 2.2 | `EstadoRemito.despachar(r, envio, usuario)` recibe además `usuario`. | Las muestras pasan a En tránsito y el historial necesita el usuario. |
| 2.3 | `EstadoMuestra.acciones_disponibles()` y `EstadoRemito.acciones_disponibles(r)` (base = lista vacía). | La UI pregunta qué botones mostrar sin `if estado == …` (sugerido en `context.md` 5.1). |
| 2.4 | `EstadoMuestra.fue_despachada()` (False en Extraída/Empaquetada; True desde En tránsito). | `OrdenDerivacion.actualizar_estado()` decide EN_PROCESO sin comparar estados. |
| 2.5 | `codigo` (nombre de la clase), `desde_nombre()`, `todos()` en ambas bases; `__eq__`/`__hash__` por tipo. | Persistencia y listados. |
| 2.6 | `Recibida.analizar()` agrega el resultado y pasa a **Analizada recién cuando la muestra tiene resultado para todos los análisis de la orden que usan su tipo de muestra**. | `registrar_resultado(r, usuario)` recibe un único resultado (diagrama), pero la consigna/`context.md` piden un formulario con todos los análisis compatibles: el formulario llama una vez por análisis y la última llamada produce la transición. |
| 2.7 | Precondiciones de despacho (sin muestras, sin precinto, temperatura de despacho fuera del rango del contenedor) lanzan `TransicionInvalidaError` desde `RemitoArmado.despachar`. Agregar una muestra a un remito ya precintado también. | Son transiciones no permitidas en ese momento. |
| 2.8 | `RemitoArmado.cerrar` exige al menos una muestra y asigna el contenedor (`DISPONIBLE → EN_USO`), como la tabla 5.3. | — |
| 2.9 | `RemitoArmado.agregar_muestra` valida capacidad del contenedor, laboratorio de destino, clínica de origen y orden vigente; luego delega en `muestra.empaquetar()` (la muestra decide). | Tabla 5.3. |
| 2.10 | `EstadoRemito.registrar_temperatura_despacho(r, t)` (base = inválido) redefinido solo en `RemitoArmado`, y `RemitoBiologico.registrar_temperatura_despacho(t)`. Permite **volver a medir** la temperatura de un remito ya precintado mientras no salió. | Si la temperatura de despacho daba fuera de rango, el remito quedaba trabado en Armado (no se podía despachar, ni agregar/quitar muestras) con el contenedor en uso. Ahora se acondiciona la conservadora, se registra una nueva medición y se despacha; la muestra nunca deja de estar Empaquetada en la clínica. **Falta en el diagrama.** |

## 3. Patrón Observer

| # | Decisión |
|---|---|
| 3.1 | Los observadores se adjuntan en **un único lugar**: `app/services/fabrica_observadores.py::adjuntar_observadores`, enganchado a los eventos `init` (creación) y `load` (lectura) de `MuestraBiologica`. Los observadores no se persisten (viven en `__dict__["_lista_observadores"]`). |
| 3.2 | `RegistroHistorial` recibe el repositorio por constructor (`HistorialRepository`, solo `agregar`/`listar_por_muestra`). Si la muestra aún no está en una sesión, la fila queda vinculada y se persiste en cascada en la misma transacción. |
| 3.3 | El primer registro `— → Extraída` (motivo “Extracción en consulta”) lo escribe `RegistroHistorial` al ejecutarse `MuestraBiologica._nacer(usuario)`, que llama a `_cambiar_estado`. Así se cumple la multiplicidad 1..* sin escribir historial a mano. |
| 3.4 | Los nombres guardados en el historial son los **nombres para mostrar** (Extraída, En tránsito…), porque es la traza que leen las personas; el reporte R3 los usa para medir tiempos. |

## 4. Trazabilidad inmutable (3 capas)

1. Dominio: `HistorialEstadoMuestraFila.__setattr__/__delattr__` bloquean cambios; `historial()` devuelve `tuple` de dataclasses `frozen`.
2. Repositorio: `HistorialRepository` sin `actualizar`/`eliminar` + listeners `before_update`/`before_delete` que lanzan `HistorialInmutableError` (subclase de `VeterinariaError`, **agregada**).
3. Base: triggers `historial_no_update` / `historial_no_delete` con `RAISE(ABORT, …)` creados en `db.init_db()`.

## 5. Cambios en entidades (firmas y métodos auxiliares)

### Clientes y mascotas
- `Titular.dar_de_baja_mascota(m)` recibe la mascota (el diagrama no tiene parámetro). Agregados: `nombre_completo()`, `dar_de_baja()` (baja lógica del titular y sus mascotas), `reactivar()`.
- `Mascota.__init__(titular, nombre, especie, sexo, fecha_nacimiento, raza, peso, numero_historia, alergias, antecedentes)`: crea la `HistoriaClinica` (composición 1–1). Un titular **dado de baja** también lanza `MascotaSinTitularError`. Agregado `edad_texto()`.
- `HistoriaClinica.vacunas_pendientes(fecha=None, catalogo=None)`: si no se pasa el catálogo de vacunas obligatorias, lo obtiene de la sesión del objeto. Agregados: `detalle_vacunas_pendientes()` (vacuna, última aplicación, vencida desde, días de atraso; dataclass auxiliar `DetalleVacunaPendiente`), `facturas()`, `ultima_aplicacion(v)`.
- `HistoriaClinica.ultima_atencion()` considera solo atenciones realizadas (en progreso o finalizadas).
- `AplicacionVacuna.esta_vigente(fecha)`: vigente si `fecha_aplicacion ≤ fecha ≤ fecha_proxima_dosis`, con `fecha_proxima_dosis = fecha_aplicacion + intervalo_refuerzo_dias`. No se permite registrar una aplicación con fecha futura.
- `HistoriaClinica.registrar_vacuna` rechaza vacunas de otra especie.

### Atención clínica
- Estados simples con **tabla de transiciones** (`_TRANSICIONES`) en `AtencionClinica`, `DerivacionCirugia`, `Factura` y `Contenedor`, en lugar de `if estado == …`.
- `AtencionClinica.__init__(mascota, clinica, profesional, inicio, fin=None, tipo, observaciones, asiste_titular, responsable_presente)`: valida superposición (validación 4), `fin > inicio` (por defecto 30 min), que el profesional trabaje en la clínica y que si no asiste el titular se indique el responsable (caso 3).
- `AtencionClinica.iniciar()` corre el control de vacunas y **devuelve** la lista de pendientes; en URGENCIA deja constancia en `observaciones`.
- `AtencionClinica.verificar_vacunas_obligatorias()` lanza `VacunasPendientesError` para CONSULTA/CONTROL y devuelve la lista para URGENCIA/VACUNACION. Se ejecuta al **iniciar** la atención (también al registrar sin turno, que crea e inicia). Reservar un turno no se bloquea, pero la UI avisa.
- `finalizar(diagnostico, peso_registrado=None, importe=None, observaciones=None)`: parámetros opcionales extra (el formulario carga peso e importe al finalizar; el peso actualiza el de la mascota).
- `cancelar(motivo)` guarda el motivo en `observaciones` (no hay atributo propio).
- `emitir_orden_derivacion(lab, analisis, prioridad, observaciones="", numero=None)` y `derivar_a_cirugia(destino, tipo, prioridad, diagnostico_presuntivo, riesgo_anestesico, estudios_prequirurgicos, numero)`: parámetros extra opcionales. Se permiten con la atención **en progreso o finalizada**.
- `emitir_comprobante_atencion(numero=None)`: solo FINALIZADA, con importe > 0 y sin factura vigente.
- Auxiliares: propiedades `mascota`, `titular`; `se_superpone_con_intervalo(inicio, fin)` (usado por `Profesional.esta_disponible` y por `se_superpone_con`), `esta_realizada()`, `esta_finalizada()`, `bloqueara_por_vacunas()`, `transiciones_posibles()`, `factura_vigente()`, `tiene_factura_vigente()`.
- `Profesional.esta_disponible(inicio, fin, excluir=None)`.

### Cirugía (opcional)
- Atributo **agregado** `DerivacionCirugia.consentimiento_registrado_por` (para guardar el `usuario` de `registrar_consentimiento(usuario)`).
- Método **agregado** `registrar_estudios_prequirurgicos(estudios)` (los estudios se pueden cargar después de la solicitud).
- `emitir_comprobante(importe, numero=None)`: recibe el importe que ingresa el usuario (`context.md`). La factura la emite la clínica de destino (la que opera).
- `cancelar(motivo)` guarda “Cancelada: …” en `motivo_rechazo` (no hay atributo propio). `programar(fecha)` exige fecha futura. Consentimiento admitido en SOLICITADA o ACEPTADA.
- Auxiliares: `mascota`, `clinica_origen`, `transiciones_posibles()`, `admite_consentimiento()`, `esta_realizada()`, `tiene_factura_vigente()`.

### Derivación y laboratorio
- `OrdenDerivacion.registrar_muestra(tipo, volumen, usuario, codigo=None, observaciones="")`.
- Regla agregada: **una muestra por tipo de muestra por orden**.
- Una orden puede existir con 0 muestras hasta registrar la extracción (la multiplicidad 1..* se cumple luego).
- `actualizar_estado()`: COMPLETADA cuando todas las muestras son finales **y** todos los tipos de muestra que requieren los análisis tienen muestra registrada (si falta registrar la orina, la orden sigue en proceso).
- `anular(motivo)`: solo si ninguna muestra fue empaquetada/despachada; el motivo queda en `observaciones`.
- Método **agregado** `emitir_comprobante(numero=None)`: factura SERVICIO_LABORATORIO con un ítem por análisis con resultado (no cobra lo rechazado).
- Auxiliares: propiedades `clinica`, `mascota`, `titular`; `analisis_para(tipo)`, `tipos_sin_muestra()`, `esta_abierta()`, `facturable()`, `resultados()`, `tiene_factura_vigente()`.
- `MuestraBiologica` auxiliares: `_nacer`, `_agregar_resultado`, `_validar_orden_vigente`, `analisis_requeridos()`, `analisis_pendientes()`, `acciones()`, `motivo_rechazo()`, `fecha_de_estado()`.
- `Laboratorio.recibir_remito(r, precinto_integro, temp, usuario, observaciones="")`: valida que el remito sea para ese laboratorio.

### Transporte
- `RemitoBiologico.agregar_muestra(m, usuario=None)`, `cerrar(p, temperatura_despacho=None)`, `despachar(e, usuario=None)` (usuario por defecto: `usuario_armador`). Agregados `acciones()` y `_cambiar_estado()`.
- Al crear el remito se valida que el contenedor sea de la clínica y esté disponible; el servicio además evita elegir un contenedor ya elegido por otro remito en armado. El contenedor pasa a EN_USO al **cerrar** (tabla 5.3) y vuelve a DISPONIBLE al recibir.
- `Precinto.verificar(integro, usuario, observaciones="")`: como no hay atributo de verificador, el usuario y las observaciones de la recepción se agregan a `Precinto.observaciones`. Solo se verifica una vez.
- `RecepcionRemito.procesar(remito, observaciones="")`; agregados `es_aceptada()` y `motivo_principal()` (para R2). Motivos: “Precinto roto” y/o “Temperatura fuera de rango (x °C; admitido a–b °C)”. La temperatura se compara con el rango del **contenedor**.
- Regla agregada en el servicio de recepción: si el **código de precinto leído** no coincide con el esperado, se trata como precinto roto (precinto violado/reemplazado).
- `Envio`: agregado `horas_transito()`; valida transportista y llegada estimada posterior al despacho.
- `Contenedor`: agregados `enviar_a_mantenimiento()`, `habilitar()`, `esta_disponible()`, `en_mantenimiento()`, `puede_ir_a_mantenimiento()`, `rango_texto()`.

### Facturación
- Atributo **agregado** `Factura.fecha_pago` (para “cobrado vs pendiente”).
- `calcular_total()` exige al menos un ítem; no se agregan ítems a facturas pagadas/anuladas; `registrar_pago` y `anular` solo desde EMITIDA.
- “No facturar dos veces” se valida en el dominio (salvo que la anterior esté ANULADA).

## 6. Excepciones

- Se usan exactamente las del diagrama. Para validaciones menores (campos obligatorios, capacidad del contenedor, doble facturación, laboratorio equivocado, etc.) se lanza la base `VeterinariaError` con un mensaje claro, en lugar de crear excepciones nuevas.
- Única excepción agregada: `HistorialInmutableError(VeterinariaError)` (la lanzan los listeners del ORM).
- `VacunasPendientesError` lleva `vacunas` y `mascota` (y copias en texto plano) para que la UI muestre la lista y ofrezca reservar un turno de VACUNACIÓN.

## 7. Reportes

| Reporte | Decisión |
|---|---|
| R1 | Cuenta atenciones **realizadas** (en progreso o finalizadas); las reservadas y canceladas no. “% derivación” = atenciones con orden de laboratorio **o** derivación a cirugía / total. |
| R2 | “Enviadas” = muestras de remitos **despachados** en el período (fecha de despacho). Si un remito tuvo precinto roto y temperatura fuera de rango, se clasifica como “Precinto roto”. |
| R3 | Tránsito = llegada real − despacho (por clínica de origen). Procesamiento = primera vez Analizada − primera vez Recibida según el historial, por tipo de análisis (cada muestra cuenta para cada análisis de su tipo). |
| R4 | Excluye ANULADAS. Cobrado = PAGADAS; pendiente = EMITIDAS. Ranking por importe facturado por tipo de análisis. |
| R5 | “Hasta” es la fecha de corte; “Desde” (opcional) filtra por fecha de vencimiento. Se calcula con el método de dominio `detalle_vacunas_pendientes()` sobre una consulta que trae mascotas activas y la clínica de la última atención (subconsulta agregada). |
| CSV | Separador `;` y BOM UTF‑8 para que abra bien en Excel en español. |
| Lab | El portal del laboratorio ve R2 y R3 filtrados a su laboratorio; el de clínica ve los 5. |

## 8. UI

- El manejador global de `VeterinariaError` (`app/main.py`) guarda el mensaje en la sesión, conserva lo cargado en el formulario y redirige a la página anterior, donde se ve un **aviso rojo**. En GET muestra una página de error con el mismo aviso.
- La UI decide qué botones mostrar preguntando al dominio (`acciones()`, `transiciones_posibles()`, `esta_realizada()`, `facturable()`…). No hay `if estado == …` en rutas ni plantillas.
- Quedan dos comparaciones `h.estado_nuevo == …` en `MuestraBiologica.motivo_rechazo()` y `fecha_de_estado()`: **leen** la traza (motivo del rechazo, fecha de un estado), no deciden transiciones. Las consultas de listados/KPIs filtran por la columna `estado` en SQL (`estado_codigo.in_(…)`), tampoco deciden transiciones.
- El laboratorio no ve las muestras rechazadas en la cola de análisis. Si se abre por URL la carga de resultados de una muestra rechazada, la pantalla lo advierte y el botón “Intentar registrar resultado igualmente” permite **demostrar** que el dominio lanza `MuestraRechazadaError`.
- Las vacunas aplicadas en una atención de VACUNACIÓN se registran al finalizarla, con la fecha de la atención (no se aceptan fechas futuras).
- Agenda: franjas de 30 minutos de 08:00 a 19:30 por profesional.

## 9. Seed

- Fechas relativas al día en que se corre (`date.today()`), con el reloj inyectable fijado para cada evento; al terminar se libera el reloj.
- 3 clínicas, 1 laboratorio, 8 profesionales, 5 vacunas (1 no obligatoria), 7 tipos de análisis, 7 contenedores (1 en mantenimiento), 11 titulares y 17 mascotas.
- ~80 atenciones (más que las ~40 sugeridas porque incluye la agenda de hoy y las atenciones que originan órdenes y cirugías), 14 órdenes, 12 remitos en todos los estados (1 con precinto roto con 2 muestras y 1 con temperatura fuera de rango), cirugías en los 6 estados y facturas pagadas/emitidas/1 anulada.
- La histopatología viaja en un contenedor de 15–25 °C (`SUR-02`), porque las biopsias en formol no van refrigeradas (el tipo de análisis tiene ese rango).
- Mascotas pensadas para la demo: **Rocco** (García, vacunas vencidas), **Mía** (Fernández, falta triple felina), **Toby** (Herrera, cachorro sin vacunar).

---

# Ronda de correcciones (documento “Errores y cosas a mejorar”)

## Reglas generales

| # | Decisión |
|---|---|
| RG.1 | Excepciones **nuevas** (heredan de `VeterinariaError`, agregar al diagrama): `DatosInvalidosError` (formato o valor inválido: DNI, teléfono, email, nombres, fechas, horarios, duraciones) y `AtencionNoModificableError` (acciones sobre atenciones que ya no las admiten). |
| RG.2 | Los avisos muestran solo el mensaje en español; el nombre de la excepción ya no se ve. Los mensajes del dominio se redactaron para el usuario (por ejemplo “Esta atención ya fue facturada (FAC-000062).”). |
| RG.3 | Confirmaciones con un **modal de Bootstrap** (Aceptar / Cancelar) declarado una vez en `base.html`; cualquier `<form data-confirm="…">` lo usa. No queda `confirm()` ni `alert()`. |
| RG.4 | Sin emojis: íconos de Bootstrap Icons. |
| RG.5 | Las respuestas HTML llevan `Cache-Control: no-store` para que al volver atrás no se vean listados viejos. Un error en una pantalla GET vuelve a la pantalla anterior con el aviso. |
| RG.6 | Validaciones de formato centralizadas en `app/domain/validaciones.py` (`nombre_persona`, `dni`, `telefono`, `email`, `obligatorio`); los formularios repiten la regla con atributos HTML (`required`, `pattern`, `minlength`, `min`, `max`). |

## Bloque A — Inicio de sesión y auditoría

| # | Decisión |
|---|---|
| A.1 | Se ingresa eligiendo solo la sede (clínica o laboratorio). El **usuario de la sesión es el nombre de la sede** y es lo que queda en la auditoría por defecto (remito armado, despacho, consentimiento). |
| A.2 | Donde importa la persona se pide en el formulario, obligatoria y solo letras (mín. 3): **Recibido por** (recepción → `RecepcionRemito.usuario_receptor` y el historial de las muestras), **Analista** (resultados → `ResultadoAnalisis.analista` y el historial) y **Colocado por** (cierre del remito → `Precinto.usuario_colocador`). Los servicios reciben ese dato en lugar del usuario de la sesión: `RecepcionService.recibir(…, recibido_por)`, `ResultadosService.cargar_resultados(…, analista)`, `EmpaquetadoService.cerrar_remito(…, colocado_por)`. |
| A.3 | La extracción de una muestra queda registrada a nombre del **profesional de la atención** (`DerivacionesService.registrar_muestra`, parámetro `usuario` opcional). |

## Bloque B — Buscadores y selectores

| # | Decisión |
|---|---|
| B.1 | **Tom Select 2.3.1** (CDN, sin build) se aplica en un único lugar (`app/web/static/app.js::crearCombo`) a **todos** los `select.form-select`, así el comportamiento es idéntico en toda la app. Se usa el plugin `dropdown_input`: al hacer clic se abre la lista con un cuadro de búsqueda arriba que filtra mientras se escribe (la lista queda abierta) y se elige con clic o Enter. En los campos obligatorios la opción vacía es solo el texto de ayuda; en los filtros (“Todos los …”) se puede elegir. |
| B.2 | El combobox de mascota se recarga con `GET /api/titulares/{id}/mascotas` (solo mascotas activas) al cambiar el titular. |
| B.3 | Profesionales y cirujanos agrupados por especialidad (`<optgroup>`) con la macro `opciones_profesionales`; el texto de la opción es solo el nombre. |
| B.4 | Los buscadores de texto de los listados usan la macro `buscador` (ícono `bi-search` gris). |

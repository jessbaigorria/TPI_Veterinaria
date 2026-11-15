# Pruebas manuales – VetRed

Checklist para recorrer **a mano** todos los flujos del sistema y anotar qué falla o qué conviene cambiar.

**Cómo usarlo**

- Marcá `[x]` cuando el caso da el resultado esperado. Si falla, dejalo en `[ ]` y escribí qué pasó en **Obs**.
  En VS Code podés ver la vista previa con `Ctrl+Shift+V`. En GitHub los checkboxes se ven como casillas.
- Cada caso tiene un ID (por ejemplo `AT-05`) para nombrarlo en el registro de fallas del final.
- Prefijos: **(+)** = camino feliz · **(−)** = el sistema **debe rechazar** la operación con un aviso rojo.
- Los códigos de remitos, muestras y órdenes son los que crea el seed. Si ya hiciste pruebas, regenerá la base:
  `run.bat --reset` (Windows) o `./run.sh --reset`.
- **Cambiar** (arriba a la derecha) vuelve a la pantalla de ingreso para cambiar de portal o de usuario.

**Datos del seed útiles**

| Qué | Datos |
|---|---|
| Clínicas y profesionales | Se ingresa eligiendo solo la sede. **Clínica Centro**: Laura Pérez, Martín Díaz, Julieta Acosta · **Clínica Norte**: Carla Sosa, Pablo Medina · **Hospital Veterinario Sur** (alta complejidad): Diego Ríos (cirugía), Valeria Luna, Tomás Ferreyra |
| Laboratorio | Laboratorio Central de Diagnóstico Veterinario. Quién recibe y quién analiza se carga en cada formulario (solo letras). |
| Mascotas con vacunas pendientes | **Rocco** (titular Juan García): Antirrábica y Séxtuple vencidas · **Mía** (Carlos Fernández): falta Triple felina · **Toby** (Martín Herrera): cachorro sin vacunar |
| Mascotas al día | Firulais, Michi, Thor, Luna, Simba, Bruno, Nina, Coco, Max, Kira, Lola, Tom, Pompón, Rocky |
| Contenedores | CEN-01 (en uso), **CEN-02** y **CEN-03** (disponibles, 2–8 °C), NOR-01 (en uso), NOR-02 (en mantenimiento), SUR-01 (reservado por REM-000012), SUR-02 (15–25 °C) |
| Remitos abiertos | **REM-000010** En tránsito (Centro, Lola, M-000013) · **REM-000011** Despachado (Norte, Tom, M-000014) · **REM-000012** Armado sin precinto (Sur, Rocky, M-000015) |
| Remitos rechazados | REM-000003 (precinto roto, M-000004 y M-000005) · REM-000004 (temperatura, M-000006) |
| Muestras para analizar | **M-000011** (Max, URGENTE, Hemograma + Perfil renal) · **M-000012** (Kira, Citología) |
| Muestra sin empaquetar | **M-000016** (Pompón, ORD-000014, Clínica Centro) |
| Cirugías | CIR-000005 Programada (Coco) · **CIR-000006** Aceptada sin consentimiento, ASA III (Bruno) · **CIR-000007** Solicitada (Max) |
| Factura anulada | FAC-000059 |

**Resumen** (completar al terminar)

| Sección | Casos | OK | Fallan | Comentario |
|---|---|---|---|---|
| 0 Instalación |  |  |  |  |
| 1 Ingreso |  |  |  |  |
| 2 Clientes |  |  |  |  |
| 3 Mascotas e historia clínica |  |  |  |  |
| 4 Agenda |  |  |  |  |
| 5 Atenciones |  |  |  |  |
| 6 Órdenes y muestras |  |  |  |  |
| 7 Envíos (remitos) |  |  |  |  |
| 8 Recepción en el laboratorio |  |  |  |  |
| 9 Resultados |  |  |  |  |
| 10 Trazabilidad |  |  |  |  |
| 11 Cirugías |  |  |  |  |
| 12 Facturación |  |  |  |  |
| 13 Reportes |  |  |  |  |
| 14 Gestión |  |  |  |  |
| 15 Inicio / KPIs |  |  |  |  |
| 16 Inmutabilidad del historial |  |  |  |  |
| 17 Interfaz general |  |  |  |  |
| 18 Flujo completo |  |  |  |  |
| 19 Ronda de correcciones |  |  |  |  |

---

## 0. Instalación y arranque

- [ ] **IN-01 (+)** Con la base borrada, ejecutar `run.bat`. → Crea `.venv`, instala dependencias, muestra “Seed cargado: 11 titulares, 17 mascotas, …” y “VetRed en http://localhost:8000”.
  - Obs:
- [ ] **IN-02 (+)** Detener con Ctrl+C y volver a ejecutar `run.bat` sin `--reset`. → Dice “La base ya tiene datos: no se siembra” y conserva lo que hiciste.
  - Obs:
- [ ] **IN-03 (+)** `run.bat --reset`. → Regenera la base con fechas relativas a hoy.
  - Obs:
- [ ] **IN-04 (+)** `.venv\Scripts\python -m pytest`. → Todos los tests pasan.
  - Obs:

## 1. Ingreso y sesión

- [ ] **LG-01 (+)** Abrir `http://localhost:8000`. → Dos tarjetas: “Entrar como Clínica” (verde azulado) y “Entrar como Laboratorio” (violeta).
  - Obs:
- [ ] **LG-02 (+)** La tarjeta de clínica tiene solo el selector de clínica y el botón “Ingresar al Portal Clínica”; la de laboratorio, solo el selector de laboratorio y “Ingresar al Portal Laboratorio”. Las dos tarjetas están centradas.
  - Obs:
- [ ] **LG-03 (+)** Entrar como Clínica Centro. → Barra verde azulada con solo “Clínica Centro” y “Cambiar”; menú lateral de clínica.
  - Obs:
- [ ] **LG-04 (+)** Cambiar → Entrar como Laboratorio. → Barra violeta con solo el nombre del laboratorio y “Cambiar”; menú de laboratorio.
  - Obs:
- [ ] **LG-05 (+)** Las acciones hechas en la clínica sin una persona específica (armar o despachar remitos, consentimiento) quedan registradas con el nombre de la sede.
  - Obs:
- [ ] **LG-06 (−)** Sin sesión (por ejemplo después de `/salir`), abrir `http://localhost:8000/clinica`. → Redirige al ingreso.
  - Obs:
- [ ] **LG-07 (−)** Logueado en el laboratorio, abrir `http://localhost:8000/clinica`. → Redirige al ingreso (no se mezclan portales).
  - Obs:
- [ ] **LG-08 (+)** Con sesión abierta, volver a `/`. → Arriba aparece “Sesión actual … Continuar · Salir”.
  - Obs:

## 2. Clientes (titulares) – Portal Clínica

- [ ] **CL-01 (+)** Clientes › buscar “García” y luego por DNI “28456123”. → Aparece Juan García en ambos casos.
  - Obs:
- [ ] **CL-02 (+)** Nuevo titular con DNI, nombre, apellido, teléfono y email. → Abre su ficha con aviso “Titular … creado”.
  - Obs:
- [ ] **CL-03 (−)** Nuevo titular con un DNI ya existente (28456123). → Aviso rojo “Ya existe un titular con DNI …”, conservando lo cargado.
  - Obs:
- [ ] **CL-04 (−)** Nuevo titular sin nombre o sin apellido. → No se guarda (campo requerido o aviso rojo).
  - Obs:
- [ ] **CL-05 (+)** Editar un titular (teléfono, dirección). → Los datos se actualizan en la ficha.
  - Obs:
- [ ] **CL-06 (−)** Editar un titular poniéndole el DNI de otro. → Aviso rojo “Ya existe otro titular con DNI …”.
  - Obs:
- [ ] **CL-07 (+)** Ficha del titular García. → Muestra datos, mascotas (Firulais “Vacunas al día”, Rocco “2 vacuna(s) pendiente(s)”) y facturas.
  - Obs:
- [ ] **CL-08 (+)** Dar de baja un titular de prueba con mascotas. → Queda “DADO DE BAJA”; sus mascotas también quedan de baja; no se borra nada.
  - Obs:
- [ ] **CL-09 (−)** Con ese titular de baja, intentar Mascotas › Nueva mascota con él. → No figura en el desplegable; si se fuerza, aviso rojo `MascotaSinTitularError`.
  - Obs:
- [ ] **CL-10 (+)** Reactivar el titular. → Vuelve a activo (las mascotas siguen de baja hasta reactivarlas una por una).
  - Obs:

## 3. Mascotas e historia clínica

- [ ] **MA-01 (+)** Mascotas › filtrar por especie Gato y buscar por nombre del titular. → El filtro funciona.
  - Obs:
- [ ] **MA-02 (+)** Nueva mascota eligiendo titular (usar el buscador del desplegable). → Se crea con historia clínica HC-0000xx y abre su ficha.
  - Obs:
- [ ] **MA-03 (−)** Nueva mascota dejando “— Sin titular —”. → Aviso rojo **`MascotaSinTitularError`**; el formulario conserva lo cargado. *(Validación 1)*
  - Obs:
- [ ] **MA-04 (−)** Nueva mascota con fecha de nacimiento futura. → Aviso rojo.
  - Obs:
- [ ] **MA-05 (+)** Desde la ficha de un titular, “Nueva mascota”. → El titular viene preseleccionado.
  - Obs:
- [ ] **MA-06 (+)** Editar mascota (raza, peso). → Se actualiza.
  - Obs:
- [ ] **MA-07 (+)** Ficha › Resumen › Cambiar titular a otro cliente. → El titular cambia; la mascota aparece en la ficha del nuevo titular.
  - Obs:
- [ ] **MA-08 (−)** Cambiar titular a “— Sin titular —”. → Aviso rojo `MascotaSinTitularError`; el titular no cambia.
  - Obs:
- [ ] **MA-09 (+)** Resumen › editar alergias, antecedentes y observaciones › Guardar historia. → Se guardan; las alergias se ven en rojo en el detalle de la atención.
  - Obs:
- [ ] **MA-10 (+)** Pestaña Atenciones. → Lista las atenciones de la mascota, con link a cada una.
  - Obs:
- [ ] **MA-11 (+)** Pestaña Vacunas de Rocco. → Banner rojo con Antirrábica y Séxtuple (Vencida, días de atraso) y botón “Reservar turno de vacunación”.
  - Obs:
- [ ] **MA-12 (+)** Pestaña Vacunas de Toby (cachorro). → Muestra pendientes según su edad (o ninguna si no llegó a la edad mínima).
  - Obs:
- [ ] **MA-13 (+)** Vacunas › Registrar vacuna aplicada (antecedente) con fecha pasada, lote y dosis. → Aparece en la tabla; si estaba pendiente y queda vigente, desaparece de pendientes.
  - Obs:
- [ ] **MA-14 (−)** Registrar vacuna aplicada con fecha futura. → Aviso rojo “La fecha de aplicación no puede ser futura”.
  - Obs:
- [ ] **MA-15 (+)** La lista de vacunas de un perro no ofrece vacunas de gato (y al revés).
  - Obs:
- [ ] **MA-16 (+)** Pestaña Laboratorio de Firulais. → Órdenes con sus muestras, la línea de tiempo y los resultados.
  - Obs:
- [ ] **MA-17 (+)** Pestaña Cirugías de Thor. → CIR-000001 Realizada.
  - Obs:
- [ ] **MA-18 (+)** Pestaña Facturas. → Comprobantes de atenciones, laboratorio y cirugías de la mascota.
  - Obs:
- [ ] **MA-19 (+)** Dar de baja una mascota. → Queda “(baja)” y no aparece al elegir mascotas para atención o turno.
  - Obs:
- [ ] **MA-20 (+)** Reactivar la mascota (con titular activo). → Vuelve a estar activa.
  - Obs:
- [ ] **MA-21 (−)** Reactivar una mascota cuyo titular está de baja. → Aviso rojo pidiendo reactivar primero al titular.
  - Obs:

## 4. Agenda (turnos)

- [ ] **AG-01 (+)** Agenda: navegar con ◀ ▶, elegir una fecha y volver con “Hoy”. → Grilla por profesional en franjas de 30 min con los turnos del día.
  - Obs:
- [ ] **AG-02 (+)** Clic en “+” de una celda libre. → Abre Reservar turno con fecha, hora y profesional precargados.
  - Obs:
- [ ] **AG-03 (+)** Reservar: titular García → mascota Firulais → Laura Pérez → mañana 14:00 → Consulta. → “Turno reservado”; aparece en la grilla como Reservada.
  - Obs:
- [ ] **AG-04 (−)** Reservar para Rocco con Laura Pérez mañana 14:15. → Aviso rojo **`TurnoSuperpuestoError`** indicando el turno con el que choca. *(Validación 4)*
  - Obs:
- [ ] **AG-05 (+)** Reservar con Laura Pérez mañana 14:30 (justo al terminar el anterior). → Se permite (turnos contiguos no se superponen).
  - Obs:
- [ ] **AG-06 (+)** Reservar con Martín Díaz mañana 14:00 (otro profesional, mismo horario). → Se permite.
  - Obs:
- [ ] **AG-07 (−)** Reservar con hora de fin anterior o igual a la de inicio. → Aviso rojo “La hora de fin debe ser posterior a la de inicio”.
  - Obs:
- [ ] **AG-08 (+)** Al elegir Rocco al reservar. → Aviso amarillo de vacunas pendientes debajo de la mascota; al reservar una Consulta o un Control, aviso amarillo de que se bloqueará al iniciar.
  - Obs:
- [ ] **AG-09 (−)** “¿Asiste el titular? No” sin completar el responsable presente. → No se permite.
  - Obs:
- [ ] **AG-10 (+)** Cancelar el turno de AG-03 con motivo. → Queda Cancelado; el motivo figura en las observaciones.
  - Obs:
- [ ] **AG-11 (+)** Volver a reservar Rocco con Laura Pérez mañana 14:00. → Se permite: un turno cancelado no bloquea el horario.
  - Obs:
- [ ] **AG-12 (−)** Cancelar sin motivo. → No se permite.
  - Obs:
- [ ] **AG-13 (+)** “Iniciar” un turno Reservado de una mascota al día. → Pasa a En progreso y abre el detalle de la atención.
  - Obs:
- [ ] **AG-14 (−)** “Iniciar” el turno de Rocco (Control) de AG-11. → Aviso rojo **`VacunasPendientesError`**; el turno sigue Reservado.
  - Obs:

## 5. Atenciones

- [ ] **AT-01 (+) Caso 1 (titular presente)**: Registrar atención → titular (con el buscador) → mascota al día → profesional → Consulta → registrar. → “Atención registrada e iniciada”; queda En progreso.
  - Obs:
- [ ] **AT-02 (+) Caso 2 (cliente frecuente con mascota nueva)**: titular → completar la sección “Nueva mascota” (ya visible) con nombre, especie, sexo y nacimiento → registrar. → Crea la mascota y la atención en un solo paso.
  - Obs:
- [ ] **AT-03 (+) Caso 3 (no asiste el titular)**: “¿Asiste el titular? No” + responsable presente. → En el detalle se ve “No – nombre del responsable”.
  - Obs:
- [ ] **AT-04 (−)** Caso 3 sin completar el responsable. → No se permite.
  - Obs:
- [ ] **AT-05 (−)** Atención tipo **Control** para **Rocco**. → Aviso rojo **`VacunasPendientesError`** con la lista y botones “Reservar turno de VACUNACIÓN” y “Atender ahora como VACUNACIÓN”; **no** se crea la atención. *(Validación 5)*
  - Obs:
- [ ] **AT-06 (−)** Lo mismo con tipo **Consulta**. → Mismo bloqueo.
  - Obs:
- [ ] **AT-07 (+)** Rocco como **Urgencia**. → Se registra; aviso amarillo con las vacunas pendientes; en Observaciones queda “⚠ Atendida por urgencia con vacunas pendientes…”.
  - Obs:
- [ ] **AT-08 (+)** Desde el aviso de AT-05, “Atender ahora como VACUNACIÓN”. → Abre el formulario con Rocco y tipo Vacunación precargados; registrar.
  - Obs:
- [ ] **AT-09 (+)** Finalizar esa vacunación: las vacunas pendientes vienen tildadas (marcadas “pendiente”); cargar lote, diagnóstico e importe. → “Atención finalizada. Se registraron 2 vacuna(s)”.
  - Obs:
- [ ] **AT-10 (+)** Ahora registrar un **Control** de Rocco (otro horario u otro profesional). → Pasa: las vacunas quedaron al día.
  - Obs:
- [ ] **AT-11 (−)** Registrar una atención con el mismo profesional y horario que otra en curso. → Aviso rojo `TurnoSuperpuestoError`.
  - Obs:
- [ ] **AT-12 (−)** Atención sin turno con fecha de inicio futura. → Aviso rojo “Una atención sin turno previo no puede tener fecha y hora de inicio futura”.
  - Obs:
- [ ] **AT-13 (−)** Finalizar sin diagnóstico. → No se permite.
  - Obs:
- [ ] **AT-14 (−)** Finalizar con importe negativo. → Aviso rojo.
  - Obs:
- [ ] **AT-15 (+)** Finalizar cargando el peso. → El peso de la mascota se actualiza en su ficha.
  - Obs:
- [ ] **AT-16 (+)** Con la atención Finalizada aparecen “Emitir orden de laboratorio”, “Derivar a cirugía” y “Emitir comprobante de atención”.
  - Obs:
- [ ] **AT-17 (+)** Con la atención En progreso aparecen “Emitir orden” y “Derivar a cirugía”, pero no el comprobante.
  - Obs:
- [ ] **AT-18 (+)** Con la atención Reservada no aparecen esas acciones; sí “Iniciar atención” y “Cancelar turno”.
  - Obs:
- [ ] **AT-19 (+)** Atenciones › filtrar por estado, tipo, fechas y nombre de mascota. → Los filtros funcionan.
  - Obs:
- [ ] **AT-20 (−)** Registrar una atención para una mascota dada de baja. → No figura en la lista; si se fuerza, aviso rojo.
  - Obs:

## 6. Órdenes de laboratorio y muestras

- [ ] **OR-01 (+)** Desde una atención En progreso o Finalizada: Emitir orden con Hemograma + Perfil renal, prioridad Normal e indicaciones clínicas. → Abre la orden ORD-… Emitida, “sin muestras”.
  - Obs:
- [ ] **OR-02 (−)** Emitir orden sin tildar ningún análisis. → Aviso rojo “La orden debe solicitar al menos un análisis”.
  - Obs:
- [ ] **OR-03 (+)** En la orden, Registrar muestra Sangre 3 ml. → Muestra M-… en **Extraída**; la línea de tiempo muestra “— → Extraída” con tu usuario y el motivo “Extracción en consulta”.
  - Obs:
- [ ] **OR-04 (−)** Registrar una segunda muestra de Sangre en la misma orden. → Aviso rojo “La orden ya tiene una muestra de sangre”.
  - Obs:
- [ ] **OR-05 (−)** Volumen 0. → Aviso rojo.
  - Obs:
- [ ] **OR-06 (+)** Orden con Hemograma + Urianálisis y solo la muestra de sangre registrada. → Aviso “Falta registrar muestra de: Orina”.
  - Obs:
- [ ] **OR-07 (+)** El selector “Tipo de muestra” solo ofrece los tipos que piden los análisis de la orden.
  - Obs:
- [ ] **OR-08 (+)** Anular una orden sin muestras empaquetadas, con motivo. → Queda Anulada; el motivo figura en las indicaciones.
  - Obs:
- [ ] **OR-09 (−)** Registrar una muestra en una orden anulada. → No se ofrece el formulario; si se fuerza, aviso rojo.
  - Obs:
- [ ] **OR-10 (−)** Intentar anular una orden cuya muestra ya está empaquetada o despachada (p. ej. ORD-000011). → No aparece “Anular”; si se fuerza, aviso rojo.
  - Obs:
- [ ] **OR-11 (+)** Órdenes lab: filtrar por estado y buscar por número. → Funciona; cada fila muestra los badges de sus muestras.
  - Obs:
- [ ] **OR-12 (+)** Clic en el código de una muestra. → Detalle de muestra con línea de tiempo, cadena de custodia y resultados.
  - Obs:

## 7. Envíos – remitos, precinto y despacho (Portal Clínica)

- [ ] **EN-01 (+)** Envíos › Armar remito (paso 1). → El desplegable de contenedores ofrece CEN-02 y CEN-03, no CEN-01 (en uso); a la derecha se listan las muestras Extraídas (M-000016).
  - Obs:
- [ ] **EN-02 (+)** Como Clínica Norte. → NOR-02 (en mantenimiento) no aparece; si no hay contenedores disponibles, el botón queda deshabilitado con aviso.
  - Obs:
- [ ] **EN-03 (+)** Crear remito con Laboratorio Central + CEN-02. → Remito REM-… **Armado**, paso 2.
  - Obs:
- [ ] **EN-04 (+)** Abrir de nuevo “Armar remito”. → CEN-02 ya no se ofrece (está reservado por el remito en armado).
  - Obs:
- [ ] **EN-05 (−)** En el paso 2, “Empaquetar” sin tildar ninguna muestra. → Aviso rojo “Tildá al menos una muestra”.
  - Obs:
- [ ] **EN-06 (+)** Tildar M-000016 y empaquetar. → La muestra pasa a **Empaquetada**; su línea de tiempo suma “Empaquetada en el remito REM-…”.
  - Obs:
- [ ] **EN-07 (−)** Capacidad: con un contenedor de capacidad baja (editarla en Gestión), agregar más muestras de las que entran. → Aviso rojo de capacidad.
  - Obs:
- [ ] **EN-08 (+)** Paso 3: cerrar con el precinto propuesto (PRE-…), 4 °C y “Colocado por” (solo letras; con números o vacío se rechaza). → “Remito cerrado con el precinto …”; precinto Íntegro; contenedor En uso; desaparece el paso 2.
  - Obs:
- [ ] **EN-09 (−)** Cerrar otro remito usando un código de precinto ya usado. → Aviso rojo “Ya existe un precinto con código …”.
  - Obs:
- [ ] **EN-10 (+)** Cerrar con 0 °C (fuera de 2–8). → Aviso amarillo; en Despachar aparece “Volver a medir”.
  - Obs:
- [ ] **EN-11 (−)** Intentar Despachar ese remito a 0 °C. → Aviso rojo **`TransicionInvalidaError`** de temperatura; la muestra sigue Empaquetada (no se pierde).
  - Obs:
- [ ] **EN-12 (+)** “Volver a medir” con 4 °C. → “Ya se puede despachar”; desaparece el formulario de nueva medición.
  - Obs:
- [ ] **EN-13 (+)** “Volver a medir” con 10 °C. → Aviso amarillo: sigue fuera de rango.
  - Obs:
- [ ] **EN-14 (−)** Despachar sin transportista. → No se permite.
  - Obs:
- [ ] **EN-15 (−)** Despachar con la llegada estimada anterior a ahora. → Aviso rojo “La llegada estimada debe ser posterior al despacho”.
  - Obs:
- [ ] **EN-16 (+)** Despachar con transportista, vehículo y llegada estimada. → Remito **Despachado**; muestras **En tránsito**; la orden pasa a **En proceso** sola (Observer).
  - Obs:
- [ ] **EN-17 (+)** Confirmar retiro (en tránsito). → Remito **En tránsito**.
  - Obs:
- [ ] **EN-18 (+)** Envíos: filtrar por estado (Armado, En tránsito agrupa Despachado + En tránsito, Recibido con observaciones). → Funciona; la columna Recepción muestra Aceptada o Rechazada con motivo.
  - Obs:
- [ ] **EN-19 (+)** Como Hospital Sur, abrir REM-000012 (Armado sin precinto). → Permite seguir empaquetando y cerrar.
  - Obs:
- [ ] **EN-20 (−)** Abrir por URL `/clinica/envios/{id}` de un remito ya recibido. → No ofrece ninguna acción (estado final).
  - Obs:

## 8. Recepción en el laboratorio (Portal Laboratorio)

- [ ] **RE-01 (+)** Recepción. → REM-000010 (y los que despachaste) con botón **Recibir**; REM-000011 aparece en gris como “esperando retiro”, sin botón.
  - Obs:
- [ ] **RE-02 (+)** Recibir REM-000010 con el precinto esperado, “Sí, íntegro”, 5 °C y “Recibido por” (solo letras; con números o vacío se rechaza). → Pantalla verde **ACEPTADA**; M-000013 **Recibida**; el contenedor CEN-01 vuelve a Disponible.
  - Obs:
- [ ] **RE-03 (+)** Recibir un remito propio con “**No, roto**” y 5 °C. → Pantalla roja **RECHAZADA – Precinto roto**; remito “Recibido con observaciones”; todas sus muestras **Rechazadas**. *(Validación 2)*
  - Obs:
- [ ] **RE-04 (+)** Recibir con precinto íntegro pero 12 °C. → **RECHAZADA – Temperatura fuera de rango (12 °C; admitido 2–8 °C)**; muestras Rechazadas.
  - Obs:
- [ ] **RE-05 (+)** Recibir con precinto íntegro pero escribiendo otro código de precinto. → Se trata como **Precinto roto** (con constancia en las observaciones del precinto).
  - Obs:
- [ ] **RE-06 (+)** Recibir con precinto roto y temperatura fuera de rango a la vez. → El motivo incluye ambas causas.
  - Obs:
- [ ] **RE-07 (−)** Recibir sin cargar la temperatura. → No se permite.
  - Obs:
- [ ] **RE-08 (−)** Abrir por URL `/laboratorio/recepcion/{id}` de un remito ya recibido y confirmar. → Aviso rojo (el precinto ya fue verificado o la transición es inválida).
  - Obs:
- [ ] **RE-09 (−)** Abrir por URL la recepción de REM-000011 (Despachado, sin retiro confirmado) y confirmar. → Aviso rojo `TransicionInvalidaError`.
  - Obs:
- [ ] **RE-10 (+)** Recepciones: lista aceptadas y rechazadas con motivo; filtrar por resultado; abrir una. → Muestra el resultado y la lista de muestras.
  - Obs:
- [ ] **RE-11 (+)** En el Portal Clínica, el remito recibido muestra el resultado de la recepción y las muestras con su nuevo estado (mismos datos en ambos portales).
  - Obs:

## 9. Resultados de análisis (Portal Laboratorio)

- [ ] **RS-01 (+)** Muestras a analizar. → M-000011 (URGENTE) aparece primero, después M-000012 y las recibidas; no aparecen rechazadas.
  - Obs:
- [ ] **RS-02 (+)** Cargar resultados de M-000011 completando los dos bloques (Hemograma y Perfil renal) y el “Analista”. → “Estado: Analizada”; la orden ORD-000009 pasa a **Completada** sola (Observer).
  - Obs:
- [ ] **RS-03 (+)** Cargar resultados de una muestra con 2 análisis completando solo uno. → Sigue **Recibida** y vuelve al formulario con el análisis pendiente; al completar el otro pasa a Analizada.
  - Obs:
- [ ] **RS-04 (−)** Guardar sin completar ningún valor. → Aviso rojo “Hay que cargar los valores de …”.
  - Obs:
- [ ] **RS-05 (−)** Muestra rechazada (p. ej. M-000004): Trazabilidad → Ver detalle → “Intentar cargar un resultado” → completar y enviar. → La pantalla advierte que está rechazada; al enviar, aviso rojo **`MuestraRechazadaError`**. *(Validación 2)*
  - Obs:
- [ ] **RS-06 (−)** Abrir por URL la carga de resultados de una muestra ya Analizada y enviar. → Aviso rojo (`TransicionInvalidaError` o “no está pendiente”).
  - Obs:
- [ ] **RS-07 (+)** En el Portal Clínica, la ficha de la mascota (pestaña Laboratorio) y la orden muestran los resultados con analista y fecha.
  - Obs:
- [ ] **RS-08 (+)** El analista registrado (y el usuario del historial) es el nombre cargado en “Analista”.
  - Obs:

## 10. Trazabilidad

- [ ] **TR-01 (+)** Trazabilidad › buscar M-000001. → Línea de tiempo: Extraída → Empaquetada → En tránsito → Recibida → Analizada, cada paso con fecha, usuario y motivo; cadena de custodia completa (extrajo, armó, precinto y quién lo colocó, transportista, recibió, analizó).
  - Obs:
- [ ] **TR-02 (+)** Buscar REM-000003. → Las dos muestras con su línea de tiempo terminada en Rechazada por “Precinto roto”.
  - Obs:
- [ ] **TR-03 (+)** Buscar en minúsculas (`m-000001`). → La encuentra igual.
  - Obs:
- [ ] **TR-04 (−)** Buscar un código inexistente. → Aviso amarillo “No se encontró …”.
  - Obs:
- [ ] **TR-05 (+)** Las muestras que creaste en tus pruebas muestran como usuario a quien estaba logueado en cada paso (clínica o laboratorio).
  - Obs:
- [ ] **TR-06 (+)** La línea de tiempo aparece igual en: ficha de mascota (Laboratorio), detalle de orden, detalle de muestra (clínica y laboratorio) y carga de resultados.
  - Obs:

## 11. Cirugías de alta complejidad

- [ ] **CI-01 (−)** Desde una atención de Clínica Centro: Derivar a cirugía con destino **Clínica Norte**. → Aviso rojo **`DerivacionCirugiaError`** (no es de alta complejidad).
  - Obs:
- [ ] **CI-02 (−)** Derivar sin tipo de cirugía. → No se permite.
  - Obs:
- [ ] **CI-03 (+)** Derivar al Hospital Veterinario Sur (ASA II). → CIR-… **Solicitada**; aparece en Cirugías › Enviadas.
  - Obs:
- [ ] **CI-04 (+)** En Clínica Centro no existe la pestaña “Recibidas”, y en el detalle se indica que acepta y programa el hospital.
  - Obs:
- [ ] **CI-05 (+)** Cambiar a Hospital Sur · Diego Ríos → Cirugías › Recibidas. → Aparece la derivación (y CIR-000007).
  - Obs:
- [ ] **CI-06 (−)** Rechazar sin motivo. → No se permite.
  - Obs:
- [ ] **CI-07 (+)** Rechazar CIR-000007 con motivo. → **Rechazada**; el motivo se ve en el detalle.
  - Obs:
- [ ] **CI-08 (+)** Aceptar la derivación de CI-03 eligiendo cirujano. → **Aceptada** con el cirujano.
  - Obs:
- [ ] **CI-09 (−)** Programar sin consentimiento. → Aviso rojo **`DerivacionCirugiaError`** “sin el consentimiento firmado”.
  - Obs:
- [ ] **CI-10 (+)** Registrar consentimiento firmado. → “Firmado (registró …)” con tu usuario.
  - Obs:
- [ ] **CI-11 (−)** CIR-000006 (Bruno, ASA III, aceptada): registrar el consentimiento y programar sin estudios. → Aviso rojo “hay que cargar los estudios prequirúrgicos”.
  - Obs:
- [ ] **CI-12 (+)** Cargar los estudios prequirúrgicos de CIR-000006 y programar. → **Programada**.
  - Obs:
- [ ] **CI-13 (−)** Programar con fecha pasada (si el navegador lo deja). → Aviso rojo “La fecha programada debe ser futura”.
  - Obs:
- [ ] **CI-14 (−)** Registrar la cirugía sin informe. → No se permite.
  - Obs:
- [ ] **CI-15 (+)** Registrar la cirugía con informe. → **Realizada**; aparece la tarjeta Facturación.
  - Obs:
- [ ] **CI-16 (+)** Cancelar con motivo una derivación Aceptada o Programada (p. ej. CIR-000005). → **Cancelada** con “Cancelada: motivo”.
  - Obs:
- [ ] **CI-17 (+)** En una derivación Realizada, Rechazada o Cancelada no se ofrecen más acciones de estado.
  - Obs:
- [ ] **CI-18 (+)** El consentimiento también se puede registrar desde la clínica de origen mientras la derivación está Solicitada o Aceptada.
  - Obs:
- [ ] **CI-19 (+)** La clínica de origen ve en Cirugías › Enviadas el estado actualizado por el hospital.
  - Obs:

## 12. Facturación

- [ ] **FA-01 (+)** Facturación › Pendiente de facturar. → Lista atenciones finalizadas, órdenes completadas con análisis realizados y (en el hospital) cirugías realizadas sin factura.
  - Obs:
- [ ] **FA-02 (+)** Emitir el comprobante de una atención. → FAC-… con un ítem igual al importe; total correcto; sale de pendientes.
  - Obs:
- [ ] **FA-03 (−)** Volver a facturar la misma atención (desde su detalle o por URL). → Aviso rojo “Ya se facturó … (comprobante FAC-…)”.
  - Obs:
- [ ] **FA-04 (+)** Anular ese comprobante y volver a facturar la atención. → Se permite (la anterior está Anulada).
  - Obs:
- [ ] **FA-05 (+)** Registrar el pago eligiendo la forma de pago. → **Pagada**, con forma y fecha de pago.
  - Obs:
- [ ] **FA-06 (−)** Anular una factura Pagada. → No se ofrece; si se fuerza, aviso rojo.
  - Obs:
- [ ] **FA-07 (+)** Facturar una orden completada con todas sus muestras analizadas. → Un ítem por análisis con su precio; total = suma de los ítems.
  - Obs:
- [ ] **FA-08 (+)** Orden con una muestra analizada y otra rechazada. → Solo se facturan los análisis de la muestra analizada.
  - Obs:
- [ ] **FA-09 (−)** Orden con todas sus muestras rechazadas. → No aparece en pendientes; si se fuerza, aviso rojo “no hay nada para facturar”.
  - Obs:
- [ ] **FA-10 (−)** Facturar una cirugía con importe 0 o vacío. → Aviso rojo.
  - Obs:
- [ ] **FA-11 (+)** Facturar una cirugía realizada con importe (como Hospital Sur). → La factura queda emitida por el hospital.
  - Obs:
- [ ] **FA-12 (−)** Facturar una atención no finalizada (por URL). → Aviso rojo “Solo se facturan atenciones finalizadas”.
  - Obs:
- [ ] **FA-13 (+)** Comprobantes: filtrar por tipo y estado; abrir uno. → Detalle con clínica, titular, ítems, total y vínculo a la atención, orden o cirugía.
  - Obs:
- [ ] **FA-14 (+)** Montos con formato `$ 12.500,00` en todas las pantallas.
  - Obs:

## 13. Reportes

Para cada reporte comprobar: filtros (las dos fechas obligatorias, «Hasta» no menor que «Desde»), indicadores, gráfico, tabla y **Exportar PDF** (encabezado con sede y fecha, filtros, gráfico, tabla y totales). En ninguna pantalla deben aparecer las siglas R1–R5.

- [ ] **RP-01 (+)** Atenciones y derivaciones: filas por clínica y mes; barras apiladas por tipo; columnas con orden de laboratorio, derivadas a cirugía y % derivación.
  - Obs:
- [ ] **RP-02 (+)** Atenciones y derivaciones filtrado por una clínica y por un rango de fechas corto. → Cambian los números y el gráfico.
  - Obs:
- [ ] **RP-03 (+)** Muestras rechazadas: tablas por clínica, por motivo (Precinto roto / Temperatura) y por transportista, con %.
  - Obs:
- [ ] **RP-04 (+)** Después de RE-03 y RE-04, Muestras rechazadas suma esos rechazos.
  - Obs:
- [ ] **RP-05 (+)** Tiempos de tránsito: tránsito promedio, mínimo y máximo por clínica (h); procesamiento por tipo de análisis vs estimado.
  - Obs:
- [ ] **RP-06 (+)** Facturación por clínica y laboratorio: totales por clínica y tipo, cobrado vs pendiente, ranking de análisis; las facturas anuladas no suman.
  - Obs:
- [ ] **RP-07 (+)** Después de FA-02 o FA-05, Facturación por clínica y laboratorio refleja el cambio (pendiente → cobrado).
  - Obs:
- [ ] **RP-08 (+)** Vacunas pendientes: Rocco (si no lo vacunaste), Mía y Toby con días de atraso, titular y teléfono; filtros por especie y clínica de última atención.
  - Obs:
- [ ] **RP-09 (+)** Después de vacunar a Rocco (AT-09), desaparece de Vacunas pendientes.
  - Obs:
- [ ] **RP-10 (+)** Un rango de fechas sin datos. → “No hay datos para los filtros elegidos” sin error.
  - Obs:
- [ ] **RP-11 (+)** Portal Laboratorio › Reportes: solo “Muestras rechazadas” y “Tiempos de tránsito”, filtrados a su laboratorio.
  - Obs:
- [ ] **RP-12 (−)** Portal Laboratorio, abrir por URL `/laboratorio/reportes/facturacion`. → Aviso de que el laboratorio solo tiene esos dos reportes.
  - Obs:

## 14. Gestión (Portal Clínica)

- [ ] **CA-01 (+)** Pestañas Clínicas, Profesionales, Laboratorios, Tipos de análisis, Vacunas y Contenedores. → Cada una lista sus registros.
  - Obs:
- [ ] **CA-02 (+)** Nueva clínica con “Alta complejidad”. → Aparece en el ingreso y como destino válido de cirugías.
  - Obs:
- [ ] **CA-03 (+)** Nuevo profesional en una clínica. → Aparece en el ingreso de esa clínica, en la agenda y como cirujano (si es del hospital).
  - Obs:
- [ ] **CA-04 (+)** Editar un profesional y cambiarlo de clínica. → Aparece en la nueva clínica.
  - Obs:
- [ ] **CA-05 (−)** Alta sin un campo obligatorio (nombre, legajo, etc.). → Aviso rojo “El campo «…» es obligatorio”.
  - Obs:
- [ ] **CA-06 (+)** Nuevo tipo de análisis (tipo de muestra, rango de temperatura, precio). → Se ofrece al emitir órdenes.
  - Obs:
- [ ] **CA-07 (−)** Tipo de análisis con precio negativo, **al crear** y **al editar**. → Debe rechazarse en los dos casos.
  - Obs:
- [ ] **CA-08 (+)** Editar el precio de un análisis. → Las facturas nuevas usan el precio nuevo.
  - Obs:
- [ ] **CA-09 (+)** Nueva vacuna obligatoria para perros (edad mínima 8 semanas). → Pasa a figurar como pendiente en todos los perros, en la ficha y en Vacunas pendientes.
  - Obs:
- [ ] **CA-10 (+)** Marcar una vacuna como no obligatoria. → Deja de contar como pendiente.
  - Obs:
- [ ] **CA-11 (+)** Nuevo contenedor (código, capacidad, rango, clínica). → Disponible al armar remitos en esa clínica.
  - Obs:
- [ ] **CA-12 (−)** Contenedor con temperatura mínima mayor que la máxima o capacidad 0. → Aviso rojo.
  - Obs:
- [ ] **CA-13 (+)** Enviar un contenedor Disponible a mantenimiento (🔧). → En mantenimiento; no se ofrece al armar remitos.
  - Obs:
- [ ] **CA-14 (+)** Habilitar un contenedor en mantenimiento (✓). → Vuelve a Disponible.
  - Obs:
- [ ] **CA-15 (+)** Un contenedor En uso no ofrece ni mantenimiento ni habilitar.
  - Obs:
- [ ] **CA-16 (+)** Desactivar un laboratorio. → No aparece al emitir órdenes ni al armar remitos ni en el ingreso.
  - Obs:

## 15. Pantallas de inicio y KPIs

- [ ] **KP-01 (+)** Inicio clínica: 8 tarjetas (turnos de hoy, en curso, sin empaquetar, remitos armados, en camino, rechazadas en 7 días, resultados nuevos, cirugías pendientes); cada una lleva a su sección.
  - Obs:
- [ ] **KP-02 (+)** Tras rechazar un remito propio (RE-03), “Rechazadas (7 días)” sube y la tarjeta se pone roja.
  - Obs:
- [ ] **KP-03 (+)** Las tarjetas cambian al registrar turnos, empaquetar, despachar, etc.
  - Obs:
- [ ] **KP-04 (+)** Inicio laboratorio: remitos en camino, por analizar, analizadas hoy, rechazadas en 7 días, tránsito promedio del mes; listas de remitos en camino, próximas muestras y últimas recepciones.
  - Obs:
- [ ] **KP-05 (+)** Tras RS-02, “Analizadas hoy” sube y “Muestras por analizar” baja.
  - Obs:

## 16. Inmutabilidad del historial

- [ ] **IM-01 (+)** Ninguna pantalla permite editar ni borrar registros del historial de una muestra; la línea de tiempo dice “Historial inmutable”.
  - Obs:
- [ ] **IM-02 (+)** Cada cambio de estado agrega exactamente un registro al final (nunca modifica los anteriores).
  - Obs:
- [ ] **IM-03 (−)** *(Opcional, con DB Browser for SQLite u otra herramienta)* Abrir `veterinaria.db` y ejecutar `UPDATE historial_estado_muestra SET motivo='x';`. → Error “El historial de estados de la muestra es inmutable (UPDATE prohibido)”.
  - Obs:
- [ ] **IM-04 (−)** *(Opcional)* `DELETE FROM historial_estado_muestra;` → Error “(DELETE prohibido)”.
  - Obs:

## 17. Interfaz general

- [ ] **UI-01 (+)** Los errores aparecen como aviso rojo arriba, con el nombre de la excepción, y la pantalla no se rompe.
  - Obs:
- [ ] **UI-02 (+)** Después de un error, el formulario conserva lo que habías cargado.
  - Obs:
- [ ] **UI-03 (+)** Los mensajes de éxito aparecen como notificación abajo a la derecha y se van solos.
  - Obs:
- [ ] **UI-04 (+)** Colores fijos de los badges de muestra: Extraída gris · Empaquetada azul · En tránsito naranja · Recibida celeste · Analizada verde · Rechazada rojo.
  - Obs:
- [ ] **UI-05 (+)** Colores fijos de los badges de remito: Armado gris · Despachado azul · En tránsito naranja · Recibido verde · Recibido con observaciones rojo.
  - Obs:
- [ ] **UI-06 (+)** Fechas en formato `dd/mm/aaaa HH:MM`.
  - Obs:
- [ ] **UI-07 (+)** El menú lateral marca la sección activa; la barra superior muestra sede y usuario.
  - Obs:
- [ ] **UI-08 (+)** Las acciones irreversibles (bajas, cancelar, anular, rechazar) piden confirmación.
  - Obs:
- [ ] **UI-09 (+)** Con la ventana angosta (o desde el celular) la app sigue siendo usable.
  - Obs:
- [ ] **UI-10 (−)** Abrir una URL con un id inexistente (p. ej. `/clinica/mascotas/9999`). → Página de error “No existe …”, no un error técnico.
  - Obs:

## 18. Flujo completo de punta a punta

Recorrer seguido, sin regenerar la base (es el escenario de demo de la sección 7 del README):

- [ ] **E2E-01** Turno y turno superpuesto (AG-03, AG-04).
  - Obs:
- [ ] **E2E-02** Control de Rocco bloqueado → vacunación → control permitido (AT-05, AT-08, AT-09, AT-10).
  - Obs:
- [ ] **E2E-03** Mascota sin titular (MA-03).
  - Obs:
- [ ] **E2E-04** Orden Hemograma + Perfil renal → muestra Extraída (OR-01, OR-03).
  - Obs:
- [ ] **E2E-05** Remito → precinto → despacho → retiro (EN-03, EN-06, EN-08, EN-16, EN-17).
  - Obs:
- [ ] **E2E-06** Laboratorio: recepción aceptada → resultados → Analizada → orden Completada (RE-02, RS-02).
  - Obs:
- [ ] **E2E-07** Repetir con precinto roto → Rechazada → `MuestraRechazadaError` (RE-03, RS-05).
  - Obs:
- [ ] **E2E-08** Línea de tiempo de las dos muestras (TR-01).
  - Obs:
- [ ] **E2E-09** Cirugía Centro → Hospital Sur: aceptar, consentimiento, programar, realizar, facturar (CI-03 a CI-15, FA-11).
  - Obs:
- [ ] **E2E-10** Facturar atención y laboratorio; abrir los cinco reportes (FA-02, FA-07, sección 13).
  - Obs:

---

## 19. Ronda de correcciones del grupo

- [ ] **RC-A** Ingreso solo por sede; tarjetas centradas; la barra muestra solo la sede y “Cambiar”.
  - Obs:
- [ ] **RC-B1** En Registrar atención, Reservar turno, Nueva mascota, Emitir orden, Armar remito, Derivar a cirugía, Facturación y filtros: al hacer clic se abre la lista con un buscador, al escribir se filtra con la lista abierta y se elige con clic o Enter.
  - Obs:
- [ ] **RC-B2/B3** Al elegir titular, la mascota muestra solo sus mascotas activas; los profesionales aparecen agrupados por especialidad y sin la especialidad entre paréntesis.
  - Obs:
- [ ] **RC-B4/B5** Los filtros dicen “Todos los estados”, “Todos los tipos”, etc.; no hay lupas de color.
  - Obs:
- [ ] **RC-C1/C2** «Hasta» no admite una fecha menor que «Desde» (y si se fuerza por URL, aviso rojo); un filtro sin resultados muestra “No hay registros para mostrar”.
  - Obs:
- [ ] **RC-C3** Reservar turno ofrece Consulta, Control, Vacunación, Cirugía y Otro (sin Urgencia); sin turno, todos.
  - Obs:
- [ ] **RC-C4/C5** Al elegir la hora de inicio o el tipo, el fin se completa solo (30 min consulta/control/vacunación, 60 min cirugía/otro/urgencia) y no se puede alargar; el campo de hora acepta minutos de a 5 sin el error de “00:15 y 00:30”.
  - Obs:
- [ ] **RC-C6** Ninguna atención empieza antes de las 08:00 ni termina después de las 19:00.
  - Obs:
- [ ] **RC-C7** No se puede reservar un turno en el pasado ni hoy en una hora ya pasada.
  - Obs:
- [ ] **RC-C8** La atención sin turno propone la hora actual y no acepta una futura.
  - Obs:
- [ ] **RC-D** Título “Registrar atención médica sin turno previo”; sin recuadro de casos; “¿No existe? Crear titular” debajo del titular vuelve con el titular elegido; la mascota nueva está desplegada; “Responsable presente” solo letras (mín. 3).
  - Obs:
- [ ] **RC-E** No se puede finalizar sin importe o con 0; con la atención finalizada no aparecen “Emitir orden” ni “Derivar a cirugía” (solo el comprobante).
  - Obs:
- [ ] **RC-F** Titular: todos los campos obligatorios, DNI con máscara `## ### ###` (7 u 8 dígitos, no repetido), teléfono solo números (8 a 15), email válido, nombre y apellido solo letras; la baja pide confirmación en un modal que lista las mascotas.
  - Obs:
- [ ] **RC-G** El botón dice “Registrar muestra”; los badges de estado se ven como píldoras normales y centradas.
  - Obs:
- [ ] **RC-H** Reportes con nombre (sin R1–R5), fechas obligatorias y “Exportar PDF”.
  - Obs:
- [ ] **RC-I** El menú dice “Gestión”; al emitir un comprobante desde “Pendiente de facturar”, el ítem desaparece de la lista y el mensaje dice “Comprobante FAC-… emitido”.
  - Obs:
- [ ] **RC-General** Ningún mensaje muestra nombres técnicos (VeterinariaError, …Error); las confirmaciones son modales con Aceptar / Cancelar.
  - Obs:

## Registro de fallas y cambios

| ID caso | Qué pasó | Qué se esperaba | Gravedad (alta/media/baja) | ¿Bug o mejora? | Estado |
|---|---|---|---|---|---|
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

## Ideas de mejora (fuera de lo que pide la consigna)

-
-
-

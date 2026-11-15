# Trazabilidad de requisitos

Requisito de la consigna (Tema 2) → dónde está implementado → en qué pantalla se usa → qué test lo verifica.
Rutas de pantallas relativas a `http://localhost:8000`. Tests en `tests/`.

## Procesos de negocio obligatorios

| # | Requisito | Clase / método (dominio y servicio) | Pantalla | Test |
|---|---|---|---|---|
| P1 | Administrar clientes | `Titular` (`personas.py`): `agregar_mascota`, `mascotas_activas`, `dar_de_baja`; `ClientesService.crear_titular/actualizar_titular/dar_de_baja/reactivar/buscar` | Clínica › Clientes (`/clinica/clientes`, ficha `/clinica/clientes/{id}`) | `test_web.py::test_paginas_portal_clinica`, `datos_servicios.py` (alta por servicio) |
| P2 | Administrar mascotas e historias clínicas (incluye vacunas aplicadas) | `Mascota.__init__`, `cambiar_titular`, `edad_en_semanas`; `HistoriaClinica.agregar_atencion/registrar_vacuna/vacunas_pendientes/atenciones_en_periodo/ultima_atencion/ordenes_derivacion/resultados_laboratorio/derivaciones_cirugia`; `AplicacionVacuna.esta_vigente`; `MascotasService` | Clínica › Mascotas: ficha con pestañas Resumen · Atenciones · Vacunas · Laboratorio · Cirugías · Facturas (`/clinica/mascotas/{id}?tab=…`) | `test_validaciones.py` (vacunas, titular), `test_web.py` (todas las pestañas) |
| P3a | Registrar consultas médicas | `AtencionClinica.__init__/iniciar/finalizar/cancelar`; `AtencionesService.reservar_turno/iniciar/registrar_sin_turno/finalizar` | Clínica › Agenda (`/clinica/agenda`, `/clinica/agenda/nuevo`), Atenciones (`/clinica/atenciones/nueva` con casos 1-2-3, detalle `/clinica/atenciones/{id}`) | `test_validaciones.py`, `test_demo.py` pasos 1-2 |
| P3b | Emitir órdenes de derivación de laboratorio | `AtencionClinica.emitir_orden_derivacion`, `OrdenDerivacion.agregar_analisis/registrar_muestra/anular`; `DerivacionesService` | Atención › “Emitir orden de laboratorio” (`/clinica/ordenes/nueva?atencion=`), Órdenes lab (`/clinica/ordenes/{id}`: registrar muestra) | `test_coordinacion.py`, `test_demo.py` paso 4 |
| P4 | Empaquetar muestras en contenedores con remito y precinto | `RemitoBiologico.__init__/agregar_muestra/cerrar`, `RemitoArmado.agregar_muestra/cerrar`, `Extraida.empaquetar`, `Precinto.__init__`, `Contenedor.asignar`; `EmpaquetadoService` | Clínica › Envíos › “Armar remito” (3 pasos: `/clinica/envios/nuevo` → `/clinica/envios/{id}`) | `test_state_remito.py`, `test_coordinacion.py`, `test_demo.py` paso 5 |
| P5 | Registrar la cadena de envío | `RemitoBiologico.despachar/iniciar_transito`, `RemitoArmado.despachar`, `RemitoDespachado.iniciar_transito`, `Empaquetada.despachar`, `Envio`; `EnviosService.despachar/confirmar_retiro` | Envíos › remito: “Despachar” y “Confirmar retiro (en tránsito)” | `test_state_remito.py::test_flujo_completo`, `test_coordinacion.py::test_flujo_feliz_completo` |
| P6 | Recepción en el laboratorio verificando el precinto | `Laboratorio.recibir_remito` → `RecepcionRemito.procesar` → `Precinto.verificar` → `RemitoEnTransito.recibir` → `EnTransito.recibir/rechazar`; `RecepcionService.recibir` | Laboratorio › Recepción (`/laboratorio/recepcion`, formulario `/laboratorio/recepcion/{id}`, resultado `/laboratorio/recepciones/{id}`) | `test_state_remito.py` (precinto/temperatura), `test_validaciones.py::test_precinto_roto_impide_cargar_resultados`, `test_demo.py` pasos 6-7 |
| P7a | Registrar resultados de análisis | `MuestraBiologica.registrar_resultado` → `Recibida.analizar` → `Analizada`; `ResultadoAnalisis`; `ResultadosService.cargar_resultados/cola_de_analisis` | Laboratorio › Muestras a analizar (`/laboratorio/muestras`, `/laboratorio/muestras/{id}/resultados`) | `test_state_muestra.py`, `test_coordinacion.py`, `test_demo.py` paso 6 |
| P7b | Emitir comprobantes de atención | `AtencionClinica.emitir_comprobante_atencion`, `OrdenDerivacion.emitir_comprobante`, `DerivacionCirugia.emitir_comprobante`, `Factura.agregar_item/calcular_total/registrar_pago/anular`, `ItemFactura.subtotal`; `FacturacionService` | Clínica › Facturación (`/clinica/facturacion`: pendientes y comprobantes, detalle `/clinica/facturacion/{id}`) | `test_facturacion.py`, `test_demo.py` paso 10 |

## Proceso opcional elegido

| Requisito | Clase / método | Pantalla | Test |
|---|---|---|---|
| Derivaciones para cirugías de alta complejidad | `AtencionClinica.derivar_a_cirugia`; `DerivacionCirugia.registrar_consentimiento/aceptar/rechazar/programar/registrar_cirugia/cancelar/emitir_comprobante`; `CirugiasService` | Atención › “Derivar a cirugía” (`/clinica/cirugias/nueva?atencion=`); Clínica › Cirugías (pestañas Enviadas / Recibidas, detalle `/clinica/cirugias/{id}`) | `test_validaciones.py` (sección 6), `test_facturacion.py::test_factura_cirugia_y_pago`, `test_demo.py` paso 9 |

## Validaciones de negocio

| # | Validación | Dónde vive | Cómo se ve en la UI | Test |
|---|---|---|---|---|
| V1 | Toda mascota debe tener un responsable | `Mascota.__init__`, `Mascota.cambiar_titular` → `MascotaSinTitularError` | Alta de mascota / cambio de titular: aviso rojo `MascotaSinTitularError` | `test_validaciones.py::test_mascota_sin_titular_*`, `test_web.py::test_error_de_negocio_se_muestra_en_aviso_rojo`, `test_demo.py` paso 3 |
| V2 | Precinto roto → Muestra Rechazada; no se procesa | `RecepcionRemito.procesar`, `RemitoEnTransito.recibir`, `EnTransito.rechazar`, `Rechazada.analizar` → `MuestraRechazadaError` | Recepción: pantalla roja “RECHAZADA – Precinto roto”; la cola no ofrece la muestra; intento manual → aviso rojo `MuestraRechazadaError` | `test_state_remito.py::test_precinto_roto_rechaza_todas_las_muestras`, `test_validaciones.py::test_precinto_roto_impide_cargar_resultados`, `test_demo.py` paso 7 |
| V3 | Trazabilidad inmutable de estados | State (`_cambiar_estado` único) + Observer (`RegistroHistorial`) + `HistorialEstadoMuestraFila` (sin setters) + `HistorialRepository` (solo agrega) + listeners ORM + triggers SQLite (`db.py`) | Línea de tiempo en ficha de mascota, orden, muestra y Laboratorio › Trazabilidad (`/laboratorio/trazabilidad?codigo=`) con el aviso “Historial inmutable” | `test_observer.py`, `test_inmutabilidad_dominio.py`, `test_inmutabilidad.py`, `test_seed.py::test_toda_muestra_tiene_historial_consistente` |
| V4 | Sin superposición de turnos | `AtencionClinica.__init__` → `Profesional.esta_disponible` → `AtencionClinica.se_superpone_con_intervalo`; `se_superpone_con` → `TurnoSuperpuestoError` | Reservar turno / registrar atención: aviso rojo con el turno que choca | `test_validaciones.py::test_turno_superpuesto`, `::test_turno_cancelado_no_bloquea`, `test_demo.py` paso 1 |
| V5 | Esquema de vacunas obligatorias al registrar atenciones | `AtencionClinica.iniciar` → `verificar_vacunas_obligatorias` → `HistoriaClinica.vacunas_pendientes` → `Vacuna.corresponde_a`, `AplicacionVacuna.esta_vigente` → `VacunasPendientesError` | Aviso amarillo al elegir la mascota; CONSULTA/CONTROL → aviso rojo con la lista y botones “Reservar turno de VACUNACIÓN” / “Atender ahora como VACUNACIÓN”; URGENCIA → advertencia amarilla y constancia en observaciones; VACUNACIÓN → registra aplicaciones | `test_validaciones.py` (sección 5), `test_demo.py` paso 2 |
| V6 | Cirugía: destino de alta complejidad, consentimiento, ASA ≥ III con estudios | `DerivacionCirugia.__init__`, `DerivacionCirugia.programar` → `DerivacionCirugiaError` | Derivar / Programar: aviso rojo | `test_validaciones.py::test_derivar_a_clinica_sin_alta_complejidad`, `::test_programar_sin_consentimiento`, `::test_asa_iii_sin_estudios_no_se_programa`, `test_demo.py` paso 9 |

## Ciclo de vida y patrones de diseño

| Requisito | Implementación | Test |
|---|---|---|
| Ciclo de vida de la muestra (Extraída → Empaquetada → En tránsito → Recibida → Analizada / Rechazada) | **State**: `app/domain/estados/estado_muestra.py` (`EstadoMuestra`, `Extraida`, `Empaquetada`, `EnTransito`, `Recibida`, `Analizada`, `Rechazada`) | `test_state_muestra.py` (válidas, todas las inválidas parametrizadas, finales, rehidratación) |
| Ciclo de vida del remito (Armado → Despachado → En tránsito → Recibido / Recibido con observaciones) | **State**: `app/domain/estados/estado_remito.py` (`EstadoRemito`, `RemitoArmado`, `RemitoDespachado`, `RemitoEnTransito`, `RemitoRecibido`, `RemitoRecibidoConObservaciones`) | `test_state_remito.py` |
| Estados persistidos y rehidratados | Columna `estado` (string) + `@orm.reconstructor` en `MuestraBiologica._rehidratar_estado` y `RemitoBiologico._rehidratar_estado` | `test_persistencia.py` |
| Consecuencias desacopladas de los cambios de estado | **Observer**: `app/domain/observadores/observadores_muestra.py` (`ObservadorMuestra`, `RegistroHistorial`, `ActualizadorEstadoOrden`); fábrica única `app/services/fabrica_observadores.py` | `test_observer.py`, `test_persistencia.py::test_estado_se_persiste_como_string_y_se_rehidrata` |
| Muestra, remito y precinto: estados independientes pero coordinados | `RemitoArmado.despachar`, `RemitoEnTransito.recibir`, `RecepcionRemito.procesar`, `Precinto.verificar`, `Contenedor.asignar/liberar` | `test_coordinacion.py`, `test_state_remito.py` (sección coordinación) |

## Reportes

| # | Reporte | Implementación | Pantalla | Test |
|---|---|---|---|---|
| 1 | Atenciones y derivaciones | `app/reportes/r1_atenciones.py` | `/clinica/reportes/atenciones` | `test_reportes.py::test_r1_*` |
| 2 | Muestras rechazadas | `app/reportes/r2_rechazos.py` | `/clinica/reportes/rechazos`, `/laboratorio/reportes/rechazos` | `test_reportes.py::test_r2_rechazos_por_transporte` |
| 3 | Tiempos de tránsito | `app/reportes/r3_tiempos.py` | `/clinica/reportes/tiempos`, `/laboratorio/reportes/tiempos` | `test_reportes.py::test_r3_tiempos` |
| 4 | Facturación por clínica y laboratorio | `app/reportes/r4_facturacion.py` | `/clinica/reportes/facturacion` | `test_reportes.py::test_r4_facturacion` |
| 5 | Vacunas pendientes | `app/reportes/r5_vacunas.py` | `/clinica/reportes/vacunas` | `test_reportes.py::test_r5_vacunas_pendientes` |
| — | Filtros, gráfico (Chart.js), tabla, PDF y CSV | `app/reportes/comun.py` (`Filtro`, `Grafico.config`, `a_csv`), `app/reportes/pdf.py` (`a_pdf`), `componentes/reporte.html` | `?formato=pdf` / `?formato=csv` en cada reporte | `test_correcciones_web.py::test_h4_*`, `test_reportes.py::test_csv`, `test_web.py::test_csv_de_reportes` |

## Arquitectura y criterios generales

| Requisito | Dónde | Test |
|---|---|---|
| Dos portales sobre los mismos datos | `app/web/routers/portal_clinica.py`, `portal_laboratorio.py`; `base.html` (barra verde azulada / violeta) | `test_web.py`, `test_demo.py` (la clínica despacha y el laboratorio recibe) |
| Usuario de sesión en toda la auditoría | `app/web/sesion.py` → servicios (`usuario`, `usuario_armador`, `usuario_colocador`, `usuario_receptor`, `analista`) | `test_observer.py::test_cada_cambio_crea_exactamente_un_registro`, `test_persistencia.py::test_muestra_recargada_sigue_registrando_historial` |
| Manejo global de `VeterinariaError` | `app/main.py::manejar_error_negocio` | `test_web.py::test_error_de_negocio_se_muestra_en_aviso_rojo` |
| Seed creado a través de los servicios con 60 días de historia | `app/seed.py` + reloj inyectable `app/domain/reloj.py` | `test_seed.py` |

## Ronda de correcciones del grupo (documento “Errores y cosas a mejorar”)

Tests: `test_correcciones_web.py` (por HTTP con el seed), `test_horarios.py`, `test_validaciones_datos.py`,
`test_validaciones.py`, `test_seed.py`, `test_interfaz_limpia.py` (greps sobre plantillas y código).

| Punto | Cómo se resolvió | Pantalla | Test |
|---|---|---|---|
| Reglas generales | `DatosInvalidosError` y `AtencionNoModificableError`; avisos sin nombres técnicos; modal de Bootstrap (`base.html` + `app.js`); íconos en lugar de emojis; `Cache-Control: no-store` (`main.py`) | Todas | `test_interfaz_limpia.py`, `test_web.py::test_error_de_negocio_se_muestra_en_aviso_rojo` |
| A1–A3 | Login solo con la sede; tarjetas centradas (`login.html`, `.login-centro`) | `/` | `test_a1_a2_login_solo_sede` |
| A4 | Usuario de sesión = sede; **Recibido por**, **Analista**, **Colocado por** obligatorios (solo letras) en servicios y formularios; extracción a nombre del profesional | Recepción, Cargar resultados, Remito | `test_a4_*`, `test_validaciones_datos.py::test_nombre_persona_*` |
| B1 | Tom Select en todos los `select.form-select` (`app.js::crearCombo`, plugin `dropdown_input`) | Todas las pantallas con selectores | `test_b1_tom_select_en_toda_la_app` |
| B2 | API `/api/titulares/{id}/mascotas` con mascotas activas; recarga del combobox | Registrar atención, Reservar turno | `test_b2_api_devuelve_solo_mascotas_activas` |
| B3 | Macro `opciones_profesionales` con `<optgroup>` por especialidad | Reservar turno, Registrar atención, Aceptar cirugía | `test_b3_profesionales_agrupados_por_especialidad` |
| B4–B5 | “Todos los estados/tipos/…”; macro `buscador` con ícono gris | Listados y reportes | `test_b4_filtros_dicen_todos`, `test_b5_sin_lupa_emoji` |
| C1 | `validar_rango_fechas`; `min` de «Hasta» sigue a «Desde» | Atenciones, Reportes | `test_horarios.py::test_c1_*`, `test_c1_listado_rango_invertido_muestra_error`, `test_h3_*` |
| C2 | Estado vacío “No hay registros para mostrar” | Listados, Reportes | `test_c2_listado_vacio_muestra_estado_vacio` |
| C3 | `TipoAtencion.CIRUGIA` y `OTRO`; `TIPOS_RESERVABLES` sin Urgencia | Reservar turno, Registrar atención | `test_c3_*` |
| C4–C5 | `DURACION_MAXIMA_MINUTOS`, `_validar_horario`, `fin_sugerido`; JS autocompleta el fin; `step=300` | Reservar turno, Registrar atención | `test_c4_*`, `test_c5_*` |
| C6 | Horario 08:00–19:00 (`HORA_APERTURA`, `HORA_CIERRE`) | Ídem | `test_c6_*` |
| C7 | `AtencionClinica.reservar`: inicio posterior a ahora | Reservar turno | `test_c7_*` |
| C8 | `AtencionClinica.registrar_sin_turno`: inicio actual o pasado | Registrar atención | `test_c8_*` |
| C9 | Superposición sin cambios, sumada a las reglas nuevas | Ídem | `test_c9_superposicion_sigue_vigente` |
| C10 | Seed con horarios y duraciones válidos (reloj inyectable) | — | `test_seed.py::test_seed_respeta_horarios_y_duraciones` |
| D1–D6 | Título nuevo, sin recuadro de casos, “Crear titular” con `?next=`, mascota nueva desplegada (una u otra), responsable solo letras | Registrar atención | `test_d1_d2_d6_*`, `test_d3_*`, `test_d4_*`, `test_d5_*` |
| E1 | `finalizar()` exige importe > 0 | Atención | `test_e1_*`, `test_validaciones.py::test_finalizar_exige_importe_mayor_a_cero` |
| E2–E3 | Órdenes y derivaciones solo EN_PROGRESO (`AtencionNoModificableError`); pantalla ordenada | Atención, Nueva orden, Derivar | `test_e2_*`, `test_e3_*`, `test_validaciones.py::test_ordenes_y_derivaciones_solo_en_progreso` |
| E4 | Seed: derivaciones antes de finalizar, sin importes 0 | — | `test_e4_*` |
| F1 | `Titular.actualizar_datos` + `validaciones` (DNI, teléfono, email, letras) + DNI único; máscara de DNI | Clientes | `test_f1_*`, `test_validaciones_datos.py` |
| F2 | Modal de baja con la lista de mascotas | Ficha de titular y de mascota | `test_f2_baja_con_modal_que_lista_mascotas` |
| F3 | Nueva mascota sin textos técnicos, titular preseleccionado | Nueva mascota | `test_f3_*` |
| G1–G2 | “Registrar muestra”; badges `inline-flex` alineados | Orden, Atención y demás | `test_g1_*`, `test_g2_*` |
| H1–H2 | Nombres de reportes en interfaz y rutas | Reportes (clínica y laboratorio) | `test_h1_h2_sin_siglas_r1_r5` |
| H3 | Fechas obligatorias y rango | Reportes | `test_h3_fechas_obligatorias_y_rango` |
| H4 | Exportar PDF con ReportLab (`app/reportes/pdf.py`) | Reportes | `test_h4_exportar_pdf`, `test_h4_pdf_contenido` |
| I1 | “Gestión” en menú, título, migas y ruta `/clinica/gestion` | Gestión | `test_i1_catalogos_ahora_es_gestion` |
| I2 | POST → redirect → GET en facturación; pendientes sin lo facturado; mensajes claros | Facturación | `test_i2_*` |

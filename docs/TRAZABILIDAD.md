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
| R1 | Atenciones clínicas y derivaciones realizadas | `app/reportes/r1_atenciones.py` | `/clinica/reportes/r1` | `test_reportes.py::test_r1_*` |
| R2 | Muestras rechazadas por fallas en el transporte | `app/reportes/r2_rechazos.py` | `/clinica/reportes/r2`, `/laboratorio/reportes/r2` | `test_reportes.py::test_r2_rechazos_por_transporte` |
| R3 | Tiempo promedio de tránsito y procesamiento | `app/reportes/r3_tiempos.py` | `/clinica/reportes/r3`, `/laboratorio/reportes/r3` | `test_reportes.py::test_r3_tiempos` |
| R4 | Facturación por clínica y servicios de laboratorio | `app/reportes/r4_facturacion.py` | `/clinica/reportes/r4` | `test_reportes.py::test_r4_facturacion` |
| R5 | Vacunas pendientes por mascota | `app/reportes/r5_vacunas.py` | `/clinica/reportes/r5` | `test_reportes.py::test_r5_vacunas_pendientes` |
| — | Filtros, gráfico (Chart.js), tabla y CSV | `app/reportes/comun.py` (`Filtro`, `Grafico.config`, `a_csv`), `app/web/templates/componentes/reporte.html` | `?formato=csv` en cada reporte | `test_reportes.py::test_csv`, `test_web.py::test_csv_de_reportes` |

## Arquitectura y criterios generales

| Requisito | Dónde | Test |
|---|---|---|
| Dos portales sobre los mismos datos | `app/web/routers/portal_clinica.py`, `portal_laboratorio.py`; `base.html` (barra verde azulada / violeta) | `test_web.py`, `test_demo.py` (la clínica despacha y el laboratorio recibe) |
| Usuario de sesión en toda la auditoría | `app/web/sesion.py` → servicios (`usuario`, `usuario_armador`, `usuario_colocador`, `usuario_receptor`, `analista`) | `test_observer.py::test_cada_cambio_crea_exactamente_un_registro`, `test_persistencia.py::test_muestra_recargada_sigue_registrando_historial` |
| Manejo global de `VeterinariaError` | `app/main.py::manejar_error_negocio` | `test_web.py::test_error_de_negocio_se_muestra_en_aviso_rojo` |
| Seed creado a través de los servicios con 60 días de historia | `app/seed.py` + reloj inyectable `app/domain/reloj.py` | `test_seed.py` |

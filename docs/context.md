# context.md — Sistema Veterinaria: Red de Clínicas y Derivación de Laboratorio

> **Para Claude Code:** este documento es el contexto completo del TP. Junto a él recibís la consigna (`tema2.pdf`),
> el documento de alcances del grupo (`Presentacion-grupo_30.docx`) y el diagrama de clases (`diagrama_clases_v2.drawio`).
> **Orden de prioridad si algo choca:** 1) consigna → 2) diagrama de clases → 3) documento de alcances → 4) las decisiones de este archivo.
> Si tenés que desviarte del diagrama (por ejemplo, un método auxiliar extra), hacelo, pero **anotalo en `docs/DECISIONES.md`**
> para que el grupo actualice el diagrama.

---

## 1. Datos del trabajo

| | |
|---|---|
| Materia | Desarrollo de Aplicaciones con Objetos (DAO) – Ingeniería en Sistemas de Información |
| Trabajo | TP Integrador 2026 – **Tema 2: Veterinaria – Red de Clínicas y Derivación de Laboratorio** |
| Grupo | **30** |
| Integrantes | 95028 Alvaretto Caterina · 85621 Alvarez Castillo Franco · 401824 Baigorria Jesica · 98118 Blady Octavio Agustín · 96095 Nasimbera Fabrizio |
| Lenguaje | **Python** (elegido por el grupo) |
| Patrones de diseño elegidos | **State** (ciclo de vida de la muestra y del remito) y **Observer** (trazabilidad: historial + actualización de la orden) |
| Proceso opcional elegido | **Administrar derivaciones para cirugías de alta complejidad** |

---

## 2. La consigna (resumen fiel)

**Contexto.** Una red de clínicas veterinarias atiende consultas, controles y urgencias. Cuando se requieren análisis complejos,
las muestras biológicas se derivan a un **laboratorio central**, manteniendo la **cadena de custodia** y las condiciones sanitarias
para que la muestra siga siendo viable. Se requiere un sistema que integre la atención clínica con la derivación, el transporte seguro
de muestras y la recepción de resultados, con **trazabilidad completa desde la extracción hasta el diagnóstico**.

**Procesos de negocio obligatorios**
1. Administrar clientes.
2. Administrar mascotas y sus historias clínicas.
3. Registrar consultas médicas y emitir órdenes de derivación de laboratorio.
4. Empaquetar muestras biológicas en conservadoras isotérmicas (contenedores) generando un **remito biológico** y un **precinto sanitario**.
5. Registrar la cadena de envío desde la clínica hacia el laboratorio central.
6. Registrar la recepción en el laboratorio, verificando el estado del precinto para garantizar la viabilidad de la muestra.
7. Registrar resultados de análisis y emitir comprobantes de atención.

**Procesos opcionales** (el grupo eligió solo el último): recordatorios · internaciones · stock de conservadoras e insumos ·
agenda completa de profesionales del laboratorio · **derivaciones para cirugías de alta complejidad**.

**Validaciones de negocio (todas obligatorias)**
1. Toda mascota debe tener un responsable asociado.
2. Impedir el procesamiento de muestras si el precinto sanitario llega roto (cambio de estado a **Muestra Rechazada**).
3. Mantener la **trazabilidad inmutable** de estados de la muestra (Extraída, Empaquetada, En tránsito, Recibida, Analizada).
4. Evitar superposición de turnos en la agenda médica.
5. Controlar el esquema de vacunas obligatorias al registrar atenciones.

**Reportes sugeridos:** atenciones clínicas y derivaciones realizadas · muestras rechazadas por fallas en el transporte ·
tratamientos aplicados y vacunas pendientes · facturación desglosada por clínica y servicios de laboratorio ·
tiempo promedio de tránsito y procesamiento de muestras.

**Consideraciones:** modelar el transporte seguro de muestras como **núcleo de trazabilidad y cambio de estados**.
**El ciclo de vida de la muestra y del remito biológico se evalúa críticamente.** Obligatorio: **≥ 2 patrones de diseño**,
**≥ 4 reportes no triviales**, todos los procesos obligatorios y todas las validaciones.

---

## 3. Alcance acordado por el grupo (del documento de alcances)

**Objetivo:** gestionar de punta a punta la atención de una red de clínicas veterinarias y su derivación de análisis a un laboratorio
central, asegurando la trazabilidad e integridad de cada muestra (extracción, empaquetado, envío, recepción, análisis o rechazo);
centralizar titulares, mascotas e historias clínicas; controlar las reglas de negocio (responsable obligatorio, turnos sin superposición,
vacunas al día, precinto íntegro); derivar pacientes a cirugías de alta complejidad dentro de la red y emitir comprobantes.

**Incluido**
- Los 7 procesos obligatorios (incluye registro de vacunas aplicadas en la historia clínica).
- Opcional: derivación a cirugía de alta complejidad desde una atención, hacia una clínica de la red habilitada
  (`alta_complejidad = True`). Se registran riesgo anestésico (ASA), estudios prequirúrgicos y consentimiento del titular;
  recién entonces se programa. Luego se registra el informe quirúrgico y se factura.
- Las 5 validaciones.
- State para muestra y remito; Observer para desacoplar los cambios de estado de sus consecuencias
  (registro del historial y actualización del estado de la orden). Muestra, remito y precinto con **estados independientes pero coordinados**.
- 5 reportes: atenciones y derivaciones · muestras rechazadas por transporte · tiempo promedio de tránsito y procesamiento ·
  facturación por clínica y servicios de laboratorio · vacunas pendientes por mascota.

**Fuera de alcance:** recordatorios · internaciones · stock de conservadoras e insumos · agenda completa del laboratorio ·
pasarelas de pago · integración con logística externa · reporte de “tratamientos aplicados” (no se modela clase Tratamiento).
La agenda de las clínicas se resuelve solo con lo necesario para evitar superposiciones: **la AtencionClinica en estado RESERVADA funciona como turno.**

---

## 4. Modelo de dominio (copia fiel del diagrama de clases)

Notación: `-` privado, `+` público, `~` paquete (en Python: `_metodo` con docstring “solo lo usan las clases de estado”).
**Las clases, atributos, métodos, enums y multiplicidades de esta sección son obligatorios.** Se pueden agregar métodos privados auxiliares.
En el código, las asociaciones se implementan como relaciones ORM (las FK no figuran en el diagrama, van en la base).
`RemitoBiologico.clinica_origen` y `Contenedor.clinica` son asociaciones a `Clinica` dibujadas como atributo.

### Clientes, mascotas e historia clínica

**Titular**
```
- dni: str
- nombre: str
- apellido: str
- direccion: str
- telefono: str
- email: str
- fecha_alta: date
- activo: bool
---
+ agregar_mascota(m: Mascota)
+ mascotas_activas(): list[Mascota]
+ dar_de_baja_mascota()
```
**Mascota**
```
- nombre: str
- especie: Especie
- raza: str
- sexo: Sexo
- fecha_nacimiento: date
- peso: float
- activa: bool
---
+ __init__(titular: Titular, ...)
+ edad_en_semanas(): int
+ cambiar_titular(t: Titular)
```
**HistoriaClinica**
```
- numero: str
- fecha_registro: date
- alergias: str
- antecedentes: str
- observaciones_generales: str
---
+ agregar_atencion(a: AtencionClinica)
+ registrar_vacuna(a: AplicacionVacuna)
+ vacunas_pendientes(): list[Vacuna]
+ atenciones_en_periodo(desde, hasta): list[AtencionClinica]
+ ultima_atencion(): AtencionClinica
+ ordenes_derivacion(): list[OrdenDerivacion]
+ resultados_laboratorio(): list[ResultadoAnalisis]
+ derivaciones_cirugia(): list[DerivacionCirugia]
```
**AplicacionVacuna**
```
- fecha_aplicacion: date
- lote: str
- dosis_numero: int
- fecha_proxima_dosis: date
---
+ esta_vigente(fecha: date): bool
```
**Vacuna**
```
- nombre: str
- especie: Especie
- obligatoria: bool
- edad_minima_semanas: int
- intervalo_refuerzo_dias: int
---
+ corresponde_a(m: Mascota): bool
```

### Atención clínica

**Clinica**
```
- nombre: str
- direccion: str
- localidad: str
- telefono: str
- email: str
- activa: bool
- alta_complejidad: bool
---
+ agregar_profesional(p: Profesional)
+ atenciones_en_periodo(desde, hasta): list[AtencionClinica]
```
**Profesional**
```
- legajo: str
- matricula: str
- dni: str
- nombre: str
- apellido: str
- especialidad: str
- telefono: str
- email: str
---
+ nombre_completo(): str
+ esta_disponible(inicio, fin): bool
```
**AtencionClinica**
```
- fecha_hora_inicio: datetime
- fecha_hora_fin: datetime
- tipo: TipoAtencion
- estado: EstadoAtencion
- diagnostico: str (lo que dice el medico)
- observaciones: str (lo que dice el cliente)
- peso_registrado: float
- importe: Decimal
- asiste_titular: bool
- responsable_presente: str
---
+ iniciar()
+ finalizar(diagnostico: str)
+ cancelar(motivo: str)
+ se_superpone_con(otra: AtencionClinica): bool
+ verificar_vacunas_obligatorias(): list[Vacuna]
+ emitir_orden_derivacion(lab, analisis, prioridad): OrdenDerivacion
+ derivar_a_cirugia(destino, tipo, prioridad): DerivacionCirugia
+ emitir_comprobante_atencion(): Factura
```

### Derivación a cirugía de alta complejidad (opcional elegido)

**DerivacionCirugia**
```
- numero: str
- fecha_solicitud: datetime
- tipo_cirugia: str
- diagnostico_presuntivo: str
- prioridad: Prioridad
- riesgo_anestesico: RiesgoAnestesico
- estudios_prequirurgicos: str
- consentimiento_firmado: bool
- fecha_programada: datetime
- estado: EstadoDerivacionCirugia
- motivo_rechazo: str
- informe_quirurgico: str
---
+ registrar_consentimiento(usuario)
+ aceptar(cirujano: Profesional)
+ rechazar(motivo: str)
+ programar(fecha: datetime)
+ registrar_cirugia(informe: str)
+ cancelar(motivo: str)
+ emitir_comprobante(): Factura
```

### Derivación y laboratorio

**OrdenDerivacion**
```
- numero: str
- fecha_emision: datetime
- prioridad: Prioridad
- observaciones: str
- estado: EstadoOrden
---
+ agregar_analisis(t: TipoAnalisis)
+ registrar_muestra(tipo, volumen, usuario): MuestraBiologica
+ actualizar_estado()
+ anular(motivo: str)
```
**TipoAnalisis**
```
- codigo: str
- nombre: str
- descripcion: str
- precio: Decimal
- tipo_muestra_requerida: TipoMuestra
- temperatura_min: float
- temperatura_max: float
- tiempo_estimado_horas: int
---
```
**MuestraBiologica**
```
- codigo: str
- tipo: TipoMuestra
- fecha_hora_extraccion: datetime
- volumen: float
- observaciones: str
- estado: EstadoMuestra
---
+ empaquetar(r: RemitoBiologico, usuario)
+ despachar(usuario)
+ recibir(usuario)
+ rechazar(motivo, usuario)
+ registrar_resultado(r: ResultadoAnalisis, usuario)
+ estado_actual(): str
+ historial(): tuple[HistorialEstadoMuestra]
+ agregar_observador(o: ObservadorMuestra)
~ cambiar_estado(nuevo: EstadoMuestra, motivo, usuario)
- notificar(anterior, nuevo, motivo, usuario)
```
**HistorialEstadoMuestra** «inmutable»
```
- fecha_hora: datetime {readOnly}
- estado_anterior: str {readOnly}
- estado_nuevo: str {readOnly}
- motivo: str {readOnly}
- usuario: str {readOnly}
---
```
**ResultadoAnalisis**
```
- fecha_hora: datetime
- valores: str
- unidad: str
- valores_referencia: str
- interpretacion: str
- analista: str
---
```
**Laboratorio**
```
- nombre: str
- direccion: str
- telefono: str
- email: str
- responsable: str
- activo: bool
---
+ recibir_remito(r, precinto_integro, temp, usuario): RecepcionRemito
```

### Transporte y cadena de custodia

**Contenedor**
```
- codigo: str
- capacidad: int
- temperatura_min: float
- temperatura_max: float
- estado: EstadoContenedor
- clinica: Clinica
---
+ asignar()
+ liberar()
+ temperatura_adecuada(t: float): bool
```
**RemitoBiologico**
```
- numero: str
- fecha_emision: datetime
- temperatura_despacho: float
- observaciones: str
- usuario_armador: str
- clinica_origen: Clinica
- estado: EstadoRemito
---
+ agregar_muestra(m: MuestraBiologica)
+ cerrar(p: Precinto)
+ despachar(e: Envio)
+ iniciar_transito()
+ recibir(r: RecepcionRemito)
+ estado_actual(): str
```
**Precinto**
```
- codigo: str
- fecha_colocacion: datetime
- estado: EstadoPrecinto
- fecha_verificacion: datetime
- usuario_colocador: str
- observaciones: str
---
+ verificar(integro: bool, usuario)
+ esta_integro(): bool
```
**Envio**
```
- fecha_hora_despacho: datetime
- fecha_hora_estimada_llegada: datetime
- fecha_hora_llegada_real: datetime
- transportista: str
- vehiculo: str
- observaciones: str
---
+ registrar_llegada(fecha_hora: datetime)
+ tiempo_transito(): timedelta
```
**RecepcionRemito**
```
- fecha_hora: datetime
- estado_precinto_observado: EstadoPrecinto
- temperatura_recepcion: float
- resultado: ResultadoRecepcion
- motivo_rechazo: str
- usuario_receptor: str
---
+ procesar(remito: RemitoBiologico)
```

### Facturación

**Factura**
```
- numero: str
- fecha_emision: datetime
- tipo: TipoComprobante
- total: Decimal
- forma_pago: FormaPago (str)
- estado: EstadoFactura
---
+ agregar_item(descripcion, cantidad, precio, tipo_analisis)
+ calcular_total(): Decimal
+ registrar_pago(f: FormaPago)
+ anular()
```
**ItemFactura**
```
- descripcion: str
- cantidad: int
- precio_unitario: Decimal
---
+ subtotal(): Decimal
```

### Patrón State – muestra

**EstadoMuestra** «abstract»
```
- nombre: str
---
+ empaquetar(m, remito, usuario)
+ despachar(m, usuario)
+ recibir(m, usuario)
+ rechazar(m, motivo, usuario)
+ analizar(m, resultado, usuario)
+ es_final(): bool
```
**Extraida**
```
---
+ empaquetar(m, remito, usuario)
```
**Empaquetada**
```
---
+ despachar(m, usuario)
```
**EnTransito**
```
---
+ recibir(m, usuario)
+ rechazar(m, motivo, usuario)
```
**Recibida**
```
---
+ analizar(m, resultado, usuario)
```
**Analizada**
```
---
+ es_final(): bool
```
**Rechazada**
```
---
+ es_final(): bool
```

### Patrón State – remito

**EstadoRemito** «abstract»
```
- nombre: str
---
+ despachar(r, envio)
+ iniciar_transito(r)
+ recibir(r, recepcion)
+ es_final(): bool
```
**RemitoArmado**
```
---
+ despachar(r, envio)
```
**RemitoDespachado**
```
---
+ iniciar_transito(r)
```
**RemitoEnTransito**
```
---
+ recibir(r, recepcion)
```
**RemitoRecibido**
```
---
+ es_final(): bool
```
**RemitoRecibidoConObservaciones**
```
---
+ es_final(): bool
```

### Patrón Observer

**ObservadorMuestra** «interface»
```
---
+ actualizar(muestra, anterior, nuevo, motivo, usuario)
```
**RegistroHistorial**
```
---
+ actualizar(muestra, anterior, nuevo, motivo, usuario)
```
**ActualizadorEstadoOrden**
```
---
+ actualizar(muestra, anterior, nuevo, motivo, usuario)
```

### Enumeraciones

| Enum | Valores |
|---|---|
| Especie | PERRO, GATO, AVE, CONEJO, OTRO |
| Sexo | MACHO, HEMBRA |
| TipoAtencion | CONSULTA, CONTROL, URGENCIA, VACUNACION |
| EstadoAtencion | RESERVADA, EN_PROGRESO, FINALIZADA, CANCELADA |
| Prioridad | NORMAL, URGENTE |
| EstadoOrden | EMITIDA, EN_PROCESO, COMPLETADA, ANULADA |
| TipoMuestra | SANGRE, ORINA, HECES, TEJIDO, HISOPADO, OTRO |
| EstadoContenedor | DISPONIBLE, EN_USO, EN_MANTENIMIENTO |
| EstadoPrecinto | INTEGRO, ROTO |
| ResultadoRecepcion | ACEPTADA, RECHAZADA |
| TipoComprobante | ATENCION_CLINICA, SERVICIO_LABORATORIO, CIRUGIA |
| FormaPago | EFECTIVO, TARJETA, TRANSFERENCIA |
| EstadoFactura | EMITIDA, PAGADA, ANULADA |
| EstadoDerivacionCirugia | SOLICITADA, ACEPTADA, PROGRAMADA, REALIZADA, RECHAZADA, CANCELADA |
| RiesgoAnestesico | ASA_I, ASA_II, ASA_III, ASA_IV, ASA_V |

### Relaciones (con multiplicidades)

| Origen | Tipo | Destino | Nombre | Mult. origen | Mult. destino |
|---|---|---|---|---|---|
| Titular | asociación → | Mascota | responsable de | 1 | 0..* |
| Mascota | composición ◆ | HistoriaClinica |  | 1 | 1 |
| HistoriaClinica | agregación ◇ | AtencionClinica | registra | 1 | 0..* |
| Clinica | agregación ◇ | Profesional | trabaja en | 1 | 1..* |
| AtencionClinica | asociación → | Clinica | se realiza en | 0..* | 1 |
| AtencionClinica | asociación → | OrdenDerivacion | emite | 1 | 0..* |
| OrdenDerivacion | asociación → | TipoAnalisis | solicita | 0..* | 1..* |
| OrdenDerivacion | asociación → | Laboratorio | destino | 0..* | 1 |
| OrdenDerivacion | composición ◆ | MuestraBiologica |  | 1 | 1..* |
| MuestraBiologica | composición ◆ | HistorialEstadoMuestra | trazabilidad | 1 | 1..* |
| MuestraBiologica | composición ◆ | ResultadoAnalisis |  | 1 | 0..* |
| ResultadoAnalisis | asociación → | TipoAnalisis |  | 0..* | 1 |
| RemitoBiologico | asociación → | MuestraBiologica | detalla | 0..1 | 1..* |
| RemitoBiologico | asociación → | Contenedor | viaja en | 0..* | 1 |
| RemitoBiologico | composición ◆ | Precinto |  | 1 | 1 |
| RemitoBiologico | composición ◆ | Envio |  | 1 | 0..1 |
| RemitoBiologico | composición ◆ | RecepcionRemito |  | 1 | 0..1 |
| RemitoBiologico | asociación → | Laboratorio | destino | 0..* | 1 |
| Factura | composición ◆ | ItemFactura |  | 1 | 1..* |
| Factura | asociación → | Titular | a nombre de | 0..* | 1 |
| Factura | asociación → | Clinica | emitida por | 0..* | 1 |
| Factura | asociación → | AtencionClinica |  | 0..* | 0..1 |
| Factura | asociación → | OrdenDerivacion |  | 0..* | 0..1 |
| ItemFactura | asociación → | TipoAnalisis |  | 0..* | 0..1 |
| MuestraBiologica | asociación → | EstadoMuestra | estado actual |  | 1 |
| RemitoBiologico | asociación → | EstadoRemito | estado actual |  | 1 |
| MuestraBiologica | agregación ◇ | ObservadorMuestra | observadores |  | 0..* |
| RegistroHistorial | dependencia | HistorialEstadoMuestra | «crea» |  |  |
| HistoriaClinica | composición ◆ | AplicacionVacuna |  | 1 | 0..* |
| AplicacionVacuna | asociación → | Vacuna |  | 0..* | 1 |
| AtencionClinica | asociación → | Profesional | atendida por | 0..* | 1 |
| AtencionClinica | asociación → | DerivacionCirugia | deriva a cirugía | 1 | 0..* |
| DerivacionCirugia | asociación → | Clinica | destino (alta complejidad) | 0..* | 1 |
| DerivacionCirugia | asociación → | Profesional | cirujano | 0..* | 0..1 |
| Factura | asociación → | DerivacionCirugia |  | 0..* | 0..1 |

Herencias: Extraida, Empaquetada, EnTransito, Recibida, Analizada, Rechazada → EstadoMuestra. RemitoArmado, RemitoDespachado, RemitoEnTransito, RemitoRecibido, RemitoRecibidoConObservaciones → EstadoRemito.
Realizaciones: RegistroHistorial y ActualizadorEstadoOrden implementan ObservadorMuestra.

### Notas del diagrama (reglas de negocio)

- Validación: crear una Mascota sin titular lanza MascotaSinTitularError. La relación con Titular reemplaza a cliente_id (la FK va en el DER).
- Trazabilidad inmutable: dataclass(frozen=True). Solo inserción: el repositorio no expone update ni delete.
- Precinto ROTO al recibir: el remito pasa a RecibidoConObservaciones y cada muestra a Rechazada. Una muestra Rechazada no admite registrar_resultado() → MuestraRechazadaError.
- Cada estado redefine solo sus transiciones válidas; las demás usan la versión base, que lanza TransicionInvalidaError. Extraída → Empaquetada → En tránsito → Recibida → Analizada En tránsito → Rechazada (precinto roto)
- Validación: al registrar la atención se llama a verificar_vacunas_obligatorias(), que usa HistoriaClinica.vacunas_pendientes(); si faltan → VacunasPendientesError.
- Validación: al reservar, esta_disponible() recorre las atenciones del profesional; si alguna se_superpone_con() → TurnoSuperpuestoError.
- Validación: el destino debe tener alta_complejidad = True y no se puede programar() sin consentimiento_firmado → DerivacionCirugiaError.

### Excepciones (hoja “opciones” del diagrama)

Todas heredan de `VeterinariaError(Exception)`:

| Excepción | Cuándo se lanza |
|---|---|
| `MascotaSinTitularError` | Crear una Mascota sin titular. |
| `TurnoSuperpuestoError` | Reservar una atención para un profesional que ya tiene otra (no cancelada) que se superpone. |
| `TransicionInvalidaError` | Cualquier transición de estado no permitida en muestra o remito (la lanza la clase base del State). |
| `MuestraRechazadaError` | Intentar registrar un resultado sobre una muestra Rechazada. |
| `VacunasPendientesError` | Registrar una atención de una mascota con vacunas obligatorias faltantes o vencidas (ver regla 7.5). |
| `DerivacionCirugiaError` | Derivar a una clínica sin `alta_complejidad`, programar sin consentimiento, o transición inválida de la derivación. |

La UI captura `VeterinariaError` en un solo lugar y muestra el mensaje en un aviso rojo, sin romper la pantalla.

---

## 5. Ciclos de vida (lo que más se evalúa)

### 5.1 MuestraBiologica — patrón State

```
[creación] → Extraida --empaquetar()--> Empaquetada --despachar()--> EnTransito --recibir()--> Recibida --analizar()--> Analizada
                                                                        └--rechazar(motivo)--> Rechazada
```
- Cada estado concreto **redefine solo sus transiciones válidas**; la clase base `EstadoMuestra` implementa todas lanzando `TransicionInvalidaError`.
- `Analizada` y `Rechazada` son finales (`es_final() = True`). `Rechazada.analizar()` lanza **`MuestraRechazadaError`** (no la genérica).
- Los métodos públicos de `MuestraBiologica` (`empaquetar`, `despachar`, `recibir`, `rechazar`, `registrar_resultado`) **solo delegan** en `self._estado`.
  `registrar_resultado(...)` delega en `estado.analizar(...)`.
- `~cambiar_estado(nuevo, motivo, usuario)` es el **único** lugar donde cambia el estado: guarda el anterior, asigna el nuevo, actualiza la columna
  persistida y llama a `-notificar(...)` (Observer).
- **Prohibido** cualquier `if estado == ...` en servicios, rutas o templates para decidir transiciones. La UI puede preguntar qué acciones están
  disponibles con un helper del estado (por ejemplo `acciones_disponibles()` en el estado base, devuelve lista vacía y cada estado devuelve las suyas);
  si lo agregás, anotalo en `DECISIONES.md`.

### 5.2 RemitoBiologico — patrón State

```
[creación] → RemitoArmado --despachar(envio)--> RemitoDespachado --iniciar_transito()--> RemitoEnTransito --recibir(recepcion)--> RemitoRecibido
                                                                                                      └--recibir(recepcion)--> RemitoRecibidoConObservaciones
```
- Mientras está **Armado** se pueden agregar muestras (`agregar_muestra`) y cerrar con precinto (`cerrar`). En cualquier otro estado eso es inválido.
  Implementalo también con State: agregá `agregar_muestra(r, m, usuario)` y `cerrar(r, precinto)` a `EstadoRemito` (base = inválido) y a `RemitoArmado`.
  **Anotalo en DECISIONES.md** (el diagrama todavía no los tiene en EstadoRemito).
- `despachar(envio)` exige: al menos 1 muestra y precinto colocado.
- `recibir(recepcion)`: si el precinto observado es **ROTO** o la temperatura de recepción está **fuera del rango del contenedor** → remito
  `RemitoRecibidoConObservaciones`; si no → `RemitoRecibido`.

### 5.3 Coordinación remito ↔ muestras ↔ precinto (estados independientes pero coordinados)

| Acción sobre el remito | Efecto en sus muestras | Efecto en otros |
|---|---|---|
| `agregar_muestra(m)` (sigue Armado) | Extraída → **Empaquetada** | La muestra queda vinculada al remito (0..1). Validar capacidad del contenedor. |
| `cerrar(precinto)` | — | Precinto creado en estado **INTEGRO**, con código único y usuario colocador. Contenedor → EN_USO. |
| `despachar(envio)` → Despachado | Empaquetada → **En tránsito** | Se crea el Envio (fecha despacho, estimada, transportista, vehículo). |
| `iniciar_transito()` → EnTransito | — | El transportista confirmó el retiro. |
| `recibir(recepcion)` → Recibido | En tránsito → **Recibida** | Precinto verificado INTEGRO; Envio registra llegada real; recepción ACEPTADA. Contenedor → DISPONIBLE. |
| `recibir(recepcion)` → RecibidoConObservaciones | En tránsito → **Rechazada** (motivo “Precinto roto” o “Temperatura fuera de rango”) | Precinto ROTO (si corresponde); recepción RECHAZADA con motivo; Envio registra llegada. Contenedor → DISPONIBLE. |

Flujo de la recepción (la clase que la dispara es `Laboratorio`):
`Laboratorio.recibir_remito(r, precinto_integro, temp, usuario)` → crea `RecepcionRemito` → `RecepcionRemito.procesar(remito)` →
`Precinto.verificar(integro, usuario)` → decide ACEPTADA/RECHAZADA y motivo → `remito.recibir(recepcion)` → el estado del remito ordena
`recibir()`/`rechazar()` a cada muestra → cada muestra notifica a sus observadores.
`Precinto.verificar` solo puede ejecutarse **una vez**.

### 5.4 Estados simples (enum, sin State)

- **AtencionClinica** (`EstadoAtencion`): `RESERVADA` (es el turno) → `EN_PROGRESO` (`iniciar`) → `FINALIZADA` (`finalizar(diagnostico)`); `RESERVADA` → `CANCELADA` (`cancelar`).
  También se puede registrar una atención **sin turno previo** (urgencia/espontánea): se crea y se inicia en el momento, igual validando superposición.
- **DerivacionCirugia** (`EstadoDerivacionCirugia`): `SOLICITADA` → `ACEPTADA` (`aceptar(cirujano)`) → `PROGRAMADA` (`programar(fecha)`, exige consentimiento) →
  `REALIZADA` (`registrar_cirugia(informe)`); `SOLICITADA` → `RECHAZADA` (`rechazar(motivo)`); `ACEPTADA`/`PROGRAMADA` → `CANCELADA`.
  Transiciones inválidas → `DerivacionCirugiaError`.
- **OrdenDerivacion** (`EstadoOrden`): `EMITIDA` al crearse → `EN_PROCESO` cuando alguna muestra sale en tránsito → `COMPLETADA` cuando **todas** sus muestras
  están en estado final (Analizada o Rechazada). `ANULADA` solo si ninguna muestra fue despachada. Lo actualiza el observer `ActualizadorEstadoOrden`.
- **Factura** (`EstadoFactura`): `EMITIDA` → `PAGADA` (`registrar_pago(forma)`) o `ANULADA` (`anular()`).
- **Contenedor** (`EstadoContenedor`): `DISPONIBLE` ↔ `EN_USO` (`asignar`/`liberar`); `EN_MANTENIMIENTO` no se puede asignar.

---

## 6. Implementación de los patrones (requisito de evaluación)

### 6.1 State

- Paquete `app/domain/estados/` con `estado_muestra.py` y `estado_remito.py`: clase base abstracta + una clase por estado, **exactamente con los nombres del diagrama**.
- **Persistencia:** en la base se guarda el nombre del estado (columna `estado`, string). Al cargar la entidad se reconstruye el objeto estado con un
  registro `{nombre: clase}` (ej. `EstadoMuestra.desde_nombre("EnTransito")`). Usá `@orm.reconstructor` de SQLAlchemy para rehidratar `self._estado`.
  Ese diccionario no cuenta como “if por estado”: no decide comportamiento.
- Nombres a mostrar en la UI: Extraída, Empaquetada, En tránsito, Recibida, Analizada, Rechazada / Armado, Despachado, En tránsito, Recibido,
  Recibido con observaciones (atributo `nombre` de cada estado).

Ejemplo de referencia (adaptar a SQLAlchemy):
```python
class EstadoMuestra(ABC):
    nombre: str = ""
    def empaquetar(self, m, remito, usuario): self._invalida("empaquetar", m)
    def despachar(self, m, usuario):          self._invalida("despachar", m)
    def recibir(self, m, usuario):            self._invalida("recibir", m)
    def rechazar(self, m, motivo, usuario):   self._invalida("rechazar", m)
    def analizar(self, m, resultado, usuario): self._invalida("analizar", m)
    def es_final(self) -> bool: return False
    def _invalida(self, accion, m):
        raise TransicionInvalidaError(f"No se puede {accion} la muestra {m.codigo}: está {self.nombre}")

class Empaquetada(EstadoMuestra):
    nombre = "Empaquetada"
    def despachar(self, m, usuario):
        m._cambiar_estado(EnTransito(), "Despachada al laboratorio", usuario)

class Rechazada(EstadoMuestra):
    nombre = "Rechazada"
    def es_final(self): return True
    def analizar(self, m, resultado, usuario):
        raise MuestraRechazadaError(f"La muestra {m.codigo} fue rechazada: no se puede analizar")
```

### 6.2 Observer

- `ObservadorMuestra` (ABC) con `actualizar(muestra, anterior, nuevo, motivo, usuario)`.
- `RegistroHistorial`: crea y guarda un `HistorialEstadoMuestra` (usa el repositorio de historial, **solo inserción**).
- `ActualizadorEstadoOrden`: llama a `muestra.orden.actualizar_estado()` (EN_PROCESO al entrar en tránsito; COMPLETADA cuando todas son finales).
- `MuestraBiologica` mantiene `_observadores` (no persistido). Los observadores se adjuntan **en un único lugar** (por ejemplo una fábrica en
  la capa de servicios, `adjuntar_observadores(muestra, session)`), que se llama al crear y al cargar muestras. Nunca se escribe el historial a mano
  fuera de `RegistroHistorial`.
- **Primer registro:** al crear la muestra se registra “— → Extraída” (motivo “Extracción en consulta”). Así se cumple la multiplicidad 1..*.

### 6.3 Trazabilidad inmutable (3 capas)

1. **Dominio:** `HistorialEstadoMuestra` sin setters; `muestra.historial()` devuelve una `tuple` de objetos inmutables
   (dataclass `frozen=True` construida a partir de las filas, como dice la nota del diagrama).
2. **Repositorio:** `HistorialRepository` solo tiene `agregar()` y `listar_por_muestra()`. **No existen** `actualizar()` ni `eliminar()`.
   Además, listeners de SQLAlchemy `before_update` / `before_delete` sobre ese modelo que lanzan excepción.
3. **Base de datos:** triggers de SQLite que hacen `RAISE(ABORT, ...)` ante UPDATE o DELETE en la tabla de historial (crearlos en `init_db`).

La muestra guarda también su estado actual en una columna (para consultar rápido); historial y estado se actualizan en la **misma transacción**.

---

## 7. Validaciones de negocio: comportamiento exacto

| # | Validación | Dónde vive | Comportamiento |
|---|---|---|---|
| 7.1 | Mascota con responsable | `Mascota.__init__(titular, ...)` | Sin titular → `MascotaSinTitularError`. En la UI no se puede crear una mascota sin elegir o crear un titular. `cambiar_titular` también exige un titular. |
| 7.2 | Precinto roto → Rechazada | `RecepcionRemito.procesar` → `RemitoEnTransito.recibir` → `EnTransito.rechazar` | Todas las muestras del remito pasan a Rechazada con motivo. Luego `registrar_resultado` → `MuestraRechazadaError`. La UI del laboratorio **no ofrece** cargar resultados de muestras rechazadas, pero el dominio igual lo impide. |
| 7.3 | Trazabilidad inmutable | State + Observer + 6.3 | Cada transición queda registrada con fecha, usuario, estado anterior, nuevo y motivo. No hay forma de editar ni borrar. |
| 7.4 | Sin superposición de turnos | `Profesional.esta_disponible(inicio, fin)` + `AtencionClinica.se_superpone_con(otra)` | Dos atenciones se superponen si `a.inicio < b.fin and b.inicio < a.fin`. Se ignoran las CANCELADAS. Si no está disponible → `TurnoSuperpuestoError`. Validar `fin > inicio`. |
| 7.5 | Vacunas obligatorias | `AtencionClinica.verificar_vacunas_obligatorias()` → `HistoriaClinica.vacunas_pendientes()` → `Vacuna.corresponde_a(m)` | Pendiente = vacuna `obligatoria` que `corresponde_a` la mascota (misma especie y `edad_en_semanas() >= edad_minima_semanas`) sin `AplicacionVacuna` vigente (vigente si `fecha_aplicacion + intervalo_refuerzo_dias >= hoy`). Se verifica **al registrar/iniciar la atención**: tipo CONSULTA o CONTROL con pendientes → `VacunasPendientesError` (la UI muestra la lista y ofrece reservar un turno de VACUNACION). URGENCIA → se permite, pero se muestra advertencia y se deja constancia en observaciones. VACUNACION → se permite y el formulario permite registrar las aplicaciones (que resuelven las pendientes). |
| 7.6 | Cirugía (opcional) | `AtencionClinica.derivar_a_cirugia` / `DerivacionCirugia.programar` | Destino sin `alta_complejidad` → `DerivacionCirugiaError`. `programar()` sin `consentimiento_firmado` → `DerivacionCirugiaError`. Regla extra: si `riesgo_anestesico` es ASA_III o mayor, no se puede programar sin `estudios_prequirurgicos` cargados. |

Otras reglas complementarias:
- **Contenedor:** solo se asigna si está DISPONIBLE; `capacidad` = máximo de muestras por remito. Al cerrar un remito se registra
  `temperatura_despacho`; si está fuera de `[temperatura_min, temperatura_max]` no se permite despachar (avisar en la UI).
- **Muestra vs análisis:** al registrar la muestra, su `tipo` debe coincidir con el `tipo_muestra_requerida` de al menos uno de los análisis de la orden.
- **Resultados:** el laboratorio carga en un solo formulario los resultados de **todos** los análisis de la orden que usan ese tipo de muestra;
  al guardar, la muestra pasa a Analizada.
- **Facturación:**
  - ATENCION_CLINICA: desde una atención FINALIZADA; 1 ítem con el `importe` de la atención.
  - SERVICIO_LABORATORIO: desde una orden COMPLETADA; un ítem por TipoAnalisis con su `precio`, **solo por las muestras analizadas**
    (no se cobra lo rechazado por fallas de transporte).
  - CIRUGIA: desde una derivación REALIZADA; el usuario ingresa el importe.
  - Una misma atención/orden/derivación no puede facturarse dos veces (salvo que la anterior esté ANULADA). `total = calcular_total()` = suma de `ItemFactura.subtotal()`.
- **Numeración automática** (string, única): `HC-000001`, `ORD-000001`, `M-000001`, `REM-000001`, `PRE-000001`, `FAC-000001`, `CIR-000001`.
- **Usuario:** todos los campos `usuario`, `usuario_armador`, `usuario_colocador`, `usuario_receptor` y `analista` se completan con el usuario de la sesión.
- **Bajas lógicas:** titulares y mascotas se desactivan (`activo`/`activa`), no se borran, porque tienen historia asociada.

---

## 8. Reportes (mínimo 4 no triviales; implementar los 5)

Todos con **filtros** (rango de fechas obligatorio + clínica/laboratorio cuando aplique), **tabla** y **gráfico** (Chart.js), y **exportación a CSV**.
Calcularlos en `app/reportes/` con consultas agregadas (no a mano en el template).

| # | Reporte | Datos | Cálculo |
|---|---|---|---|
| R1 | **Atenciones clínicas y derivaciones realizadas** | AtencionClinica → Clinica, Profesional; OrdenDerivacion; DerivacionCirugia | Por clínica y por mes: cantidad de atenciones por tipo, cantidad que generaron orden de laboratorio y derivación a cirugía, % de derivación. Gráfico de barras apiladas. |
| R2 | **Muestras rechazadas por fallas en el transporte** | RecepcionRemito (resultado, motivo) → RemitoBiologico (clinica_origen) → Envio (transportista); MuestraBiologica | Cantidad y % de muestras rechazadas sobre enviadas, por clínica de origen, por motivo (precinto roto / temperatura) y por transportista. |
| R3 | **Tiempo promedio de tránsito y procesamiento** | Envio (despacho, llegada real) + HistorialEstadoMuestra | Tránsito = llegada − despacho (promedio, mínimo, máximo por clínica de origen). Procesamiento = fecha(Analizada) − fecha(Recibida) desde el historial, promedio por tipo de análisis. Mostrar en horas. |
| R4 | **Facturación por clínica y servicios de laboratorio** | Factura (tipo, total, estado) → Clinica; ItemFactura → TipoAnalisis | Total facturado por clínica y por tipo de comprobante (excluye ANULADAS); ranking de análisis más facturados; total cobrado vs pendiente. |
| R5 | **Vacunas pendientes por mascota** | HistoriaClinica.vacunas_pendientes() → Mascota → Titular | Listado de mascotas activas con vacunas obligatorias faltantes o vencidas, días de atraso y contacto del titular; filtrable por clínica de última atención y especie. |

El portal del laboratorio ve R2 y R3 (de su laboratorio); el portal de clínica ve los 5 (filtrables por su clínica o por toda la red).

---

## 9. Arquitectura y tecnología

**Stack (simple, sin build de frontend):**

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Web | FastAPI + Uvicorn, vistas renderizadas en servidor con **Jinja2** |
| UI | **Bootstrap 5 + Bootstrap Icons** (CDN), **HTMX** opcional para acciones sin recargar, **Chart.js** (CDN) para reportes |
| Persistencia | SQLite + **SQLAlchemy 2.x** (ORM declarativo) |
| Formularios | `python-multipart` |
| Tests | **pytest** |
| Entorno | `venv` + `requirements.txt`; scripts `run.bat` (Windows) y `run.sh` |

**Capas:** `UI (rutas + templates) → services (casos de uso) → domain (entidades + State + Observer) / repositories`.
La UI **nunca** cambia estados ni accede a la base directamente; las reglas viven en el dominio.
Se usan las clases SQLAlchemy como modelos de dominio (modelo de dominio rico); State y Observer son Python puro.

**Estructura sugerida**
```
veterinaria/
├── app/
│   ├── main.py                   # FastAPI, montaje de routers, manejo global de VeterinariaError
│   ├── db.py                     # engine, sesión, init_db (incluye triggers de inmutabilidad)
│   ├── domain/
│   │   ├── enums.py
│   │   ├── excepciones.py
│   │   ├── personas.py           # Titular, Mascota, HistoriaClinica, Vacuna, AplicacionVacuna
│   │   ├── atencion.py           # Clinica, Profesional, AtencionClinica, DerivacionCirugia
│   │   ├── laboratorio.py        # OrdenDerivacion, TipoAnalisis, MuestraBiologica, HistorialEstadoMuestra, ResultadoAnalisis, Laboratorio
│   │   ├── transporte.py         # Contenedor, RemitoBiologico, Precinto, Envio, RecepcionRemito
│   │   ├── facturacion.py        # Factura, ItemFactura
│   │   ├── estados/              # PATRÓN STATE
│   │   │   ├── estado_muestra.py
│   │   │   └── estado_remito.py
│   │   └── observadores/         # PATRÓN OBSERVER
│   │       └── observadores_muestra.py   # ObservadorMuestra, RegistroHistorial, ActualizadorEstadoOrden
│   ├── repositories/             # uno por agregado; HistorialRepository solo agregar/listar
│   ├── services/                 # un servicio por proceso de negocio (clientes, mascotas, atenciones, derivaciones,
│   │                             #   empaquetado, envios, recepcion, resultados, facturacion, cirugias)
│   ├── reportes/                 # R1..R5
│   ├── web/
│   │   ├── routers/              # portal_clinica.py, portal_laboratorio.py, comunes.py
│   │   ├── templates/            # base.html, clinica/*, laboratorio/*, componentes/*
│   │   └── static/
│   └── seed.py                   # datos de prueba
├── tests/
├── docs/
│   ├── DECISIONES.md             # desvíos respecto del diagrama y decisiones tomadas
│   └── TRAZABILIDAD.md           # tabla: requisito de la consigna → clase/método → pantalla → test
├── requirements.txt
├── run.bat / run.sh
└── README.md
```

---

## 10. Propuesta de front: dos portales con estilo CRM (interfaz sencilla)

### 10.1 La idea

Una sola aplicación web con **dos portales** que reflejan los dos actores reales de la cadena de custodia:

- **Portal Clínica (veterinaria):** atiende pacientes, emite órdenes, empaqueta y despacha muestras, deriva a cirugía y factura.
- **Portal Laboratorio:** recibe remitos, verifica precinto y temperatura, analiza y carga resultados.

Los dos trabajan **sobre los mismos datos**: lo que despacha la clínica aparece en la bandeja de recepción del laboratorio, y lo que el
laboratorio recibe, rechaza o analiza aparece al instante en la ficha de la mascota y en el seguimiento de la clínica. Así la demo muestra
la trazabilidad de punta a punta con dos “pantallas” distintas.

**Ingreso (sin contraseñas, es un TP):** la pantalla `/` muestra dos tarjetas grandes:
- **Entrar como Clínica** → elegir clínica + usuario (profesional de esa clínica o “Recepción”).
- **Entrar como Laboratorio** → elegir laboratorio + nombre del operador.

Se guarda en la sesión (`SessionMiddleware` de Starlette): portal, clínica o laboratorio, y nombre de usuario (que se usa en todos los registros de auditoría).
Arriba se ve siempre “🏥 Clínica Centro · Dra. Pérez · [Cambiar]” o “🧪 Laboratorio Central · Operador: Gómez · [Cambiar]”.
Cada portal tiene un **color de barra distinto** (clínica: verde azulado; laboratorio: violeta) para distinguirlos de un vistazo.

### 10.2 Estructura común (estilo CRM)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 🏥 VetRed · Clínica Centro                    Dra. Pérez  [Cambiar]       │  ← barra superior (color del portal)
├──────────────┬───────────────────────────────────────────────────────────┤
│ ▸ Inicio     │  Título de la sección              [+ Acción principal]   │
│ ▸ Agenda     │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │  ← tarjetas KPI (en Inicio)
│ ▸ Atenciones │  │ 8 turnos│ │ 3 por   │ │ 2 en    │ │ 1 rech. │           │
│ ▸ Clientes   │  │  hoy    │ │empaquet.│ │ tránsito│ │ ⚠       │           │
│ ▸ Mascotas   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
│ ▸ Órdenes lab│  🔎 Buscar...        Filtro: [estado ▾] [fecha ▾]           │
│ ▸ Envíos     │  ┌──────────────────────────────────────────────────────┐ │
│ ▸ Cirugías   │  │ Código │ Mascota │ Estado (badge) │ Fecha │ Acciones │ │  ← tabla con búsqueda y paginado
│ ▸ Facturación│  └──────────────────────────────────────────────────────┘ │
│ ▸ Reportes   │                                                           │
│ ▸ Catálogos  │                                                           │
└──────────────┴───────────────────────────────────────────────────────────┘
```
- Menú lateral fijo, tablas con buscador y filtros, fichas de detalle con **pestañas**, botones de acción según el estado.
- **Badges de estado con color fijo** en todo el sistema: Extraída (gris) · Empaquetada (azul) · En tránsito (naranja) · Recibida (celeste) ·
  Analizada (verde) · Rechazada (rojo). Remito: Armado (gris) · Despachado (azul) · En tránsito (naranja) · Recibido (verde) · Recibido con observaciones (rojo).
- **Componente “línea de tiempo”** reutilizable que dibuja el `HistorialEstadoMuestra` (estado, fecha, usuario, motivo). Aparece en ambos portales.
- Las acciones disponibles se muestran según lo que permite el estado (consultado al dominio), y si igual se dispara una inválida, se muestra el mensaje de la excepción.
- Mensajes de éxito/error tipo “toast”. Todo en español, fechas `dd/mm/aaaa HH:MM`, montos en pesos `$ 12.500,00`.

### 10.3 Portal Clínica — pantallas

| Sección | Qué hace |
|---|---|
| **Inicio** | KPIs: turnos de hoy, atenciones en curso, muestras Extraídas sin empaquetar, remitos Armados sin despachar, remitos en tránsito, **muestras rechazadas en los últimos 7 días (alerta roja)**, resultados nuevos, cirugías pendientes. |
| **Agenda** | Turnos del día por profesional (tabla por franjas). **Reservar turno**: titular → mascota → profesional → inicio/fin → tipo → motivo. Si se superpone → aviso `TurnoSuperpuestoError`. Acciones: Iniciar / Cancelar. |
| **Atenciones** | Registrar atención (desde un turno o sin turno). Formulario basado en las notas del grupo: **Caso 1** titular presente: buscar titular (desplegable con buscador) → elegir mascota. **Caso 2** cliente frecuente con mascota nueva: botón “+ Nueva mascota” en el mismo formulario. **Caso 3** no viene el titular: “¿Asiste el titular? No” → nombre del responsable presente. Al iniciar se corre el control de vacunas (banner rojo con las pendientes si bloquea, amarillo si es urgencia). Al finalizar: diagnóstico, observaciones, peso, importe; si es VACUNACION, registrar las vacunas aplicadas. Botones después de finalizar: **Emitir orden de laboratorio · Derivar a cirugía · Emitir comprobante**. |
| **Clientes** | ABM de titulares (buscar por DNI o nombre). Ficha: datos, mascotas, facturas. Baja lógica. |
| **Mascotas** | ABM (siempre con titular). **Ficha = historia clínica** con pestañas: Resumen (alergias, antecedentes, badge de vacunas pendientes) · Atenciones · Vacunas · Laboratorio (órdenes, muestras con estado y línea de tiempo, resultados) · Cirugías · Facturas. |
| **Órdenes de laboratorio** | Lista con estado. Detalle: análisis solicitados, laboratorio, prioridad, observaciones (indicaciones clínicas), muestras con badge y línea de tiempo. **Registrar muestra** (tipo, volumen) → nace Extraída. |
| **Envíos (remitos)** | **Armar remito** en 3 pasos: (1) laboratorio destino + contenedor disponible; (2) tildar muestras Extraídas de la clínica para ese laboratorio (respetando capacidad) → quedan Empaquetadas; (3) **cerrar con precinto** (código de precinto + temperatura de despacho). Luego **Despachar** (transportista, vehículo, llegada estimada) y **Confirmar retiro (en tránsito)**. Lista de remitos con badge de estado y, cuando vuelve la recepción, su resultado. |
| **Cirugías** | Pestaña **Enviadas** (derivaciones de mi clínica) y, si mi clínica es de alta complejidad, **Recibidas**: Aceptar (elegir cirujano de mi clínica) · Rechazar · Registrar consentimiento · Programar · Registrar cirugía (informe) · Cancelar. |
| **Facturación** | “Pendiente de facturar” (atenciones finalizadas, órdenes completadas, cirugías realizadas sin factura) → Emitir. Lista de facturas: ver ítems, registrar pago (forma de pago), anular. |
| **Reportes** | R1 a R5 con filtros, gráfico, tabla y CSV. |
| **Catálogos** | Alta/edición simple de clínicas, profesionales, laboratorios, tipos de análisis, vacunas (esquema obligatorio) y contenedores. |

### 10.4 Portal Laboratorio — pantallas

| Sección | Qué hace |
|---|---|
| **Inicio** | KPIs: remitos en camino hacia este laboratorio, muestras pendientes de análisis, analizadas hoy, rechazadas en 7 días, tiempo promedio de tránsito del mes. |
| **Recepción** | Bandeja de remitos **En tránsito** hacia este laboratorio: clínica de origen, cantidad de muestras, despacho, llegada estimada, código de precinto esperado, rango de temperatura. Botón **Recibir** → formulario: código de precinto (se muestra el esperado), **¿Precinto íntegro? Sí / No** (toggle grande), temperatura medida, observaciones. Al confirmar, pantalla de resultado: **ACEPTADA** (verde) o **RECHAZADA** (rojo, con motivo) y la lista de muestras con su nuevo estado. Los remitos Despachados todavía no confirmados aparecen en gris como “esperando retiro”. |
| **Muestras a analizar** | Cola de muestras **Recibidas** (URGENTE primero, luego por antigüedad). **Cargar resultados**: un bloque por análisis de la orden compatible con el tipo de muestra (valores, unidad, valores de referencia, interpretación) → la muestra pasa a Analizada. Las rechazadas no aparecen acá. |
| **Trazabilidad** | Buscador por código de muestra o de remito → línea de tiempo completa + cadena de custodia (quién extrajo, quién armó el remito, precinto y quién lo colocó, transportista, quién recibió, quién analizó). |
| **Recepciones** | Historial de recepciones aceptadas y rechazadas con su motivo. |
| **Reportes** | R2 (rechazos por transporte) y R3 (tiempos), filtrados a este laboratorio. |

### 10.5 Reglas de simplicidad

- Nada de SPA ni build de frontend: templates Jinja2 + Bootstrap. HTMX solo si simplifica (por ejemplo, cargar las mascotas al elegir titular).
- Máximo 2 niveles de navegación. Cada proceso de negocio = 1 pantalla o 1 asistente corto.
- Validar también en el formulario (campos requeridos), pero **la regla real está en el dominio**.

---

## 11. Datos de prueba (`seed.py`) y escenario de demo

El seed debe crear los datos **a través de los servicios del dominio** (no con INSERTs directos), para que el historial de estados quede consistente.
Para fechar eventos en el pasado, usá un reloj inyectable (`app/domain/reloj.py` con `ahora()` que el seed puede fijar).

- **Clínicas:** “Clínica Centro”, “Clínica Norte” y “Hospital Veterinario Sur” (`alta_complejidad = True`).
- **Laboratorio:** “Laboratorio Central de Diagnóstico Veterinario”.
- **Profesionales:** 2 o 3 por clínica (con matrícula, especialidad; al menos un cirujano en el Hospital Sur).
- **Vacunas (esquema obligatorio):** Perro: Antirrábica (12 sem, refuerzo 365 d), Séxtuple/polivalente (8 sem, 365 d). Gato: Antirrábica (12 sem, 365 d),
  Triple felina (8 sem, 365 d). Una no obligatoria (por ejemplo Leptospirosis) para mostrar la diferencia.
- **Tipos de análisis** (con precio y conservación): Hemograma completo (SANGRE, 2–8 °C), Perfil renal (SANGRE), Perfil hepático (SANGRE),
  Urianálisis (ORINA, 2–8 °C), Coproparasitológico (HECES, 2–8 °C), Citología (HISOPADO/TEJIDO), Histopatología (TEJIDO, 15–25 °C).
- **Contenedores:** 2 por clínica (capacidad 6 a 10, rango 2–8 °C), uno en mantenimiento.
- **Titulares y mascotas:** ~10 titulares, ~15 mascotas (perros y gatos de distintas edades); varias con vacunas al día y algunas con vacunas
  vencidas o faltantes (para mostrar la validación y el R5).
- **Historia de los últimos 60 días:** ~40 atenciones en las 3 clínicas, ~12 órdenes, ~8 remitos en todos los estados, incluyendo
  **1 remito con precinto roto** y **1 con temperatura fuera de rango** (muestras Rechazadas), resultados cargados, facturas (algunas pagadas,
  una anulada) y cirugías en distintos estados (solicitada, programada, realizada, rechazada). Así los 5 reportes muestran datos reales.

**Escenario de demo (documentarlo en el README, paso a paso):**
1. Clínica Centro: reservar un turno; intentar reservar otro superpuesto para el mismo profesional → `TurnoSuperpuestoError`.
2. Registrar atención (CONTROL) de una mascota con vacunas vencidas → `VacunasPendientesError`; atenderla como VACUNACION y registrar la vacuna; ahora el control pasa.
3. Intentar crear una mascota sin titular → error.
4. Emitir orden (hemograma + perfil renal) → registrar muestra de sangre (Extraída).
5. Armar remito, cerrar con precinto, despachar, confirmar retiro.
6. Portal Laboratorio: recibir con precinto íntegro → muestras Recibidas → cargar resultados → Analizada → orden COMPLETADA (Observer).
7. Repetir 4–6 con **precinto roto** → remito “Recibido con observaciones”, muestras Rechazadas; intentar cargar resultado → `MuestraRechazadaError`.
8. Ver la línea de tiempo de ambas muestras (historial inmutable).
9. Derivar a cirugía al Hospital Sur → aceptar, consentimiento, programar, realizar → facturar.
10. Facturar atención y laboratorio; abrir los 5 reportes.

---

## 12. Tests obligatorios (pytest, base SQLite en memoria)

- **State muestra:** cada transición válida; cada transición inválida lanza `TransicionInvalidaError`; `Rechazada.analizar` lanza `MuestraRechazadaError`; finales.
- **State remito:** flujo completo; despachar sin precinto o sin muestras falla; agregar muestra fuera de Armado falla; recepción OK vs precinto roto vs temperatura.
- **Coordinación:** al despachar el remito todas sus muestras quedan En tránsito; con precinto roto todas quedan Rechazadas.
- **Observer:** cada cambio de estado crea exactamente una fila de historial con anterior/nuevo/usuario/motivo; la muestra recién creada tiene 1 registro;
  la orden pasa a EN_PROCESO y a COMPLETADA solas.
- **Inmutabilidad:** intentar UPDATE o DELETE del historial (por ORM y por SQL directo) falla.
- **Validaciones:** mascota sin titular; turnos superpuestos (y que un turno CANCELADO no bloquee); vacunas pendientes (bloquea CONTROL, permite URGENCIA con advertencia,
  VACUNACION resuelve); cirugía a clínica sin alta complejidad; programar sin consentimiento; ASA III sin estudios.
- **Facturación:** no se cobran análisis de muestras rechazadas; no se factura dos veces lo mismo; total = suma de ítems.
- **Reportes:** con datos armados en el test, R1–R5 devuelven los números esperados.
- **Smoke test web:** las páginas principales de ambos portales responden 200 con el seed cargado (`TestClient` de FastAPI).

---

## 13. Criterios de aceptación (checklist final)

- [ ] `run.bat` / `run.sh` crean el entorno, instalan dependencias, cargan el seed y levantan la app en `http://localhost:8000`.
- [ ] Los 7 procesos obligatorios se pueden hacer completos desde la UI.
- [ ] El opcional de cirugía funciona de punta a punta entre dos clínicas.
- [ ] Las 5 validaciones (+ la de cirugía) se disparan desde la UI con un mensaje claro.
- [ ] State implementado con las clases del diagrama; **no hay `if` sobre el estado** fuera de las clases de estado.
- [ ] Observer implementado con `ObservadorMuestra`, `RegistroHistorial` y `ActualizadorEstadoOrden`.
- [ ] Historial inmutable en las 3 capas.
- [ ] Los 5 reportes con filtros, gráfico, tabla y CSV.
- [ ] Dos portales (clínica y laboratorio) funcionando sobre los mismos datos.
- [ ] `pytest` pasa completo.
- [ ] `README.md` con instalación, arquitectura, dónde está cada patrón (archivo y clase), escenario de demo y capturas o descripción de pantallas.
- [ ] `docs/TRAZABILIDAD.md`: requisito de la consigna → clase/método → pantalla → test.
- [ ] `docs/DECISIONES.md`: todo desvío respecto del diagrama de clases.

---

## 14. Glosario breve del dominio

- **Anamnesis:** lo que cuenta el dueño en la consulta (en el modelo, `AtencionClinica.observaciones`, “lo que dice el cliente”).
- **Indicaciones clínicas:** lo que el veterinario le aclara al laboratorio en la orden (`OrdenDerivacion.observaciones`).
- **Cadena de custodia:** registro de quién tuvo la muestra, cuándo y en qué condiciones, desde la extracción hasta el resultado.
- **Conservadora isotérmica:** `Contenedor`, caja térmica que mantiene la temperatura durante el traslado.
- **Precinto sanitario:** sello numerado que cierra la conservadora; si llega roto, la muestra no es confiable.
- **Remito biológico:** documento que acompaña la conservadora y detalla qué muestras viajan, de dónde a dónde.
- **Riesgo anestésico ASA:** escala I (sano) a V (moribundo) usada antes de una cirugía.
- **Alta complejidad:** clínica con quirófano y especialistas para cirugías que otras sedes no pueden hacer.

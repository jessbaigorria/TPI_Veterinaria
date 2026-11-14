1. #     **Trabajo práctico integrador**

Documento de referencia de desarrollo

1. ## **1\. Grupo**

| Número de grupo:     30                        Tema: Veterinaria |
| :---- |
| Integrantes:  |
|  ***Legajo Nombre*** 95028 Alvaretto Caterina 85621 Alvarez Castillo Franco 401824 Baigorria Jesica 98118 Blady Octavio Agustín  96095 Nasimbera Fabrizio  |

   2. ## **2\. Propuesta**

### **Objetivos del sistema**

| El sistema tiene como objetivo gestionar de punta a punta la atención de una red de clínicas veterinarias y su derivación de análisis a un laboratorio central, asegurando la trazabilidad e integridad de cada muestra biológica durante todo su ciclo de vida (extracción, empaquetado, envío, recepción, análisis o rechazo). Además, centraliza la información de titulares, mascotas e historias clínicas, controla las reglas de negocio que protegen la calidad del servicio (responsable obligatorio, turnos sin superposición, vacunas al día, precinto íntegro), permite derivar pacientes a cirugías de alta complejidad dentro de la red y emite los comprobantes correspondientes  |
| :---- |

1. ### **Alcances**

| El sistema abarca los siete procesos obligatorios de la consigna: Administración de clientes. Administración de mascotas e historias clínicas, incluyendo el registro de vacunas aplicadas. Registro de consultas médicas y emisión de órdenes de derivación. Empaquetado de muestras con remito y precinto. Registro de la cadena de envío. Recepción en el laboratorio con verificación del precinto. Registro de resultados y emisión de comprobantes. Como proceso opcional se incorpora la derivación a cirugías de alta complejidad. Desde una atención clínica se puede derivar al paciente a una clínica de la red habilitada para ello. Se registran el riesgo anestésico (escala ASA), los estudios prequirúrgicos y el consentimiento del titular, y recién entonces se programa la cirugía. Luego se registra el informe quirúrgico y se emite la factura correspondiente. Validaciones de negocio contempladas. El sistema controla que: Toda mascota tenga un titular responsable; Una muestra con precinto roto no pueda procesarse y pase a *Muestra Rechazada*; Los estados de la muestra queden registrados de forma inmutable; No se superpongan los turnos de un mismo profesional; Se verifique el esquema de vacunas obligatorias al registrar una atención. Aspectos de diseño incluidos. El ciclo de vida de la muestra y del remito biológico se modela con el patrón State, de modo que cada estado defina las transiciones que permite. El patrón Observer desacopla los cambios de estado de la muestra de sus consecuencias, que son el registro del historial y la actualización del estado de la orden. La muestra, el remito y el precinto mantienen estados independientes pero coordinados. Reportes incluidos. El modelo soporta cinco reportes: Atenciones clínicas y derivaciones realizadas; Muestras rechazadas por fallas en el transporte; Tiempo promedio de tránsito y procesamiento; Facturación desglosada por clínica y por servicios de laboratorio; Vacunas pendientes por mascota. Fuera del alcance. Quedan excluidos los procesos opcionales no elegidos: El envío de recordatorios de controles, vacunas o resultados; La gestión de internaciones; La administración de stock de conservadoras e insumos médicos; La gestión de la agenda completa de profesionales del laboratorio. La agenda de las clínicas se resuelve solo con lo necesario para evitar superposiciones: la atención en estado Reservada funciona como turno. Tampoco se contempla la integración con pasarelas de pago ni con sistemas externos de logística. El reporte sugerido de “tratamientos aplicados” se deja afuera porque no se modela una clase de tratamientos. |
| :---- |

   2. ### **DER o Diagrama de Clases UML**

| Se adjunta aparte en la entrega  |
| :---- |

## 
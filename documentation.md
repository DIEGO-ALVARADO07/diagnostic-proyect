# Diagnóstico de pruebas de primer año

> Este documento conserva el planteamiento académico inicial. La descripción de lo que ya está construido, su arquitectura, instalación, API y dependencias se encuentra en la [documentación técnica](docs/README.md).

En este documento se expone claramente la necesidad que se busca abordar en el área solicitada. Esta consiste en identificar los aspectos que deben mejorar los estudiantes de nuevo ingreso (primer semestre), con el fin de ayudarlos a obtener un mejor rendimiento en las pruebas Saber Pro. Para ello, se propone una ruta complementaria de aprendizaje virtual, en la que encontrarán los cursos necesarios según los resultados de la prueba inicial. De esta manera, se busca ayudar a los estudiantes a mejorar sus resultados mediante el desarrollo de estos cursos.

En el documento se presentan las ideas principales que se buscan implementar para dar solución a esta necesidad, siguiendo una serie de pasos para desarrollar la propuesta.

Esta mejora se plantea teniendo en cuenta las cinco etapas establecidas para el óptimo progreso estudiantil:
1. **Reconocimiento:** Etapa a la cual queremos intervenir para realizar un análisis a los datos obtenidos.
2. **Fortalecimiento:** Etapa pendiente de desarrollo.
3. **Profundización:** Etapa pendiente de desarrollo.
4. **Aceleración:** Etapa pendiente de desarrollo.
5. **Resultados Saber:** Etapa pendiente de desarrollo.
---

## 1. Problemática principal
La recolección de esta información se realiza actualmente de manera genérica y, por ende, los cursos también se ofrecen de la misma manera. Con esta implementación buscamos identificar los resultados de cada estudiante y analizarlos de forma más específica, para elaborar un plan de mejora mejor estructurado. Así, el estudiante no tendrá que realizar un curso completo del área, sino únicamente el curso relacionado con el tema en el que presenta dificultades. Esto permitirá hacer más eficiente su aprendizaje y ayudarlo a mejorar su puntaje.

### Áreas
Estas son las áreas evaluadas en dicha prueba:
* **Razonamiento Cuantitativo:** Breve descripción del área.
* **Lectura Crítica:** Breve descripción del área.
* **Inglés:** Breve descripción del área.
* **Competencias Ciudadanas:** Breve descripción del área.

---

## 2. Implementación
Teniendo en cuenta la métrica de medición, buscamos crear una interfaz gráfica que permita leer y mostrar los datos de manera más clara, efectiva y eficaz. Estas reglas se especificarán en el siguiente apartado («Datos»). Aquí abordaremos el proceso de desarrollo para avanzar en la propuesta y completar las cinco etapas estipuladas por la institución Corhuila. A continuación, se describe cómo se trazará la línea de desarrollo de esta idea.

1. **Obtención de los datos:**
Debemos identificar los resultados de los estudiantes, tanto de manera individual como grupal. Todos estos datos se recibirán en un archivo de Excel.
2. **Separación de resultados:**
En este proceso se analizarán los datos obtenidos, ya que cada categorización que entrega la empresa ESE se basa en cuatro niveles. En cada nivel se define en qué nivel de desempeño o en qué tema se encuentra el estudiante. Estos niveles son los siguientes:
    * **Nivel 1:** Corresponde a un desempeño deficiente. El estudiante debe fortalecer los temas en los que presenta mayores dificultades.
    * **Nivel 2:** Corresponde a un desempeño ligeramente superior al deficiente. Aun así, el estudiante necesita fortalecer los temas en los que puede presentar dificultades.
    * **Nivel 3:** Corresponde a un buen desempeño, aunque el estudiante todavía puede mejorar.
    * **Nivel 4:** Corresponde a un desempeño sobresaliente. El estudiante puede perfeccionar algunos aspectos para mantener este nivel.

3. **Paso final:**
Una vez identificado el nivel del estudiante a partir de sus resultados, se lo categorizará para que realice determinados cursos complementarios. El objetivo es que estudie los temas de interés en los que necesita refuerzo. En esta etapa, el desarrollo permitirá asignar los cursos por nivel y área, en lugar de hacerlo por área completa.

> 💡 **Nota importante:** Aunque el estudiante obtenga un resultado de 100/100 en el área, deberá realizar al menos el curso complementario correspondiente al nivel pertinente (nivel 4).

---

## 3. Datos esperados
Para comparar elementos o mostrar especificaciones, una tabla es la mejor opción por su alta legibilidad. En la tabla, los valores numéricos representan el nivel en el que se encuentra cada estudiante:


| Estudiante \ Área | Matemáticas | Ciencias | Lenguaje | Inglés |
| :--- | :---: | :---: | :---: | :---: | 
| **Juan Pérez** | 1 | 2 | 4 | 2 |  
| **María Gómez** | 2 | 1 | 3 | 3 |
| **Carlos Ruiz** | 1 | 1 | 3 | 4 |



Los datos base para realizar la medición de resultados se tomaron del siguiente enlace:
https://app.powerbi.com/view?r=eyJrIjoiMTBjOTAxOTktMmE5OC00MDI5LTkzZTgtNGEyNzYzNzBhYWIzIiwidCI6ImQyMDBlYzA1LTNmZmItNGY1NC04YWU3LTAwMjk3MThhMWUwYyIsImMiOjR9


---

## Conclusiones
Este documento base sintetiza la propuesta y presenta una primera versión de los objetivos para iniciar su desarrollo. Por tratarse de una versión inicial, se realizarán las modificaciones necesarias a medida que se incorporen cambios o se refine la propuesta.

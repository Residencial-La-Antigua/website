# Cómo publicar una noticia

Las noticias del sitio público se publican como archivos `.md` en esta
carpeta — no se requiere tocar código ni la base de datos. Se puede crear o
editar directamente desde la interfaz web de GitHub.

## Pasos

1. En esta carpeta (`content/noticias/`), usa el botón **Add file → Create
   new file** de GitHub (o copia un artículo existente como punto de
   partida).
2. Nombra el archivo así: `AAAA-MM-DD-titulo-corto.md`, por ejemplo:
   ```
   2026-09-20-jornada-de-siembra.md
   ```
   La fecha y el "slug" (la parte después de la fecha) se toman del nombre
   del archivo — la fecha decide el orden en la lista de noticias, y el
   slug forma la URL del artículo (`/noticias/jornada-de-siembra/`). Usa
   solo minúsculas, números y guiones en el slug.
3. Escribe el contenido con este formato exacto (incluye las líneas `---`):

   ```
   ---
   title: "Título del artículo"
   summary: "Resumen corto de una o dos líneas para la lista de noticias."
   image: images/noticias/jornada-de-siembra/portada.jpg
   ---

   Aquí va el cuerpo del artículo, en **Markdown**: puedes usar títulos con
   `#`, listas, *cursivas*, **negritas** y enlaces `[texto](https://...)`.
   ```

   - `title` es obligatorio.
   - `summary` e `image` son opcionales — si no hay imagen, simplemente
     omite la línea `image`.
   - Para preparar un artículo sin publicarlo todavía, agrega la línea
     `draft: true` dentro del bloque `---`; el artículo no aparecerá en el
     sitio hasta que quites esa línea.

4. Si el artículo lleva imágenes, súbelas a
   `static/images/noticias/<slug>/` (mismo slug que el nombre del archivo)
   y referencia la ruta relativa en el campo `image`.
5. Guarda los cambios como un _pull request_ — alguien del equipo lo revisa
   y, al aprobarlo, el sitio se actualiza automáticamente.

Un artículo con errores de formato simplemente no aparece en el sitio (no
rompe la página para los demás), así que si tu noticia no aparece después
de publicarse, revisa que el formato de arriba sea el correcto.

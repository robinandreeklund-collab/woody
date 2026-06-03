# web/ – interaktivt 3D-gränssnitt

Ett webbgränssnitt som visar hela inspektionsflödet live: brädor glider i sidled
genom mätramen, skannas av line-scan + laser, och klassas av segmenteringsnätet.

**Status:** design klar, implementation ej påbörjad. Se **[DESIGN.md](DESIGN.md)**
för fullständig plan (arkitektur, FastAPI-backend, react-three-fiber-frontend,
WebSocket-datakontrakt och milstolpar).

Valda upplägg: Python-backend (FastAPI) som återanvänder `../src`, live
on-the-fly-generering och inferens, strömmat över WebSocket. Byggs i faser 0–4
enligt DESIGN.md, en commit per fas.

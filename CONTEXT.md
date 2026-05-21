# pyDpVision — Context for AI Agents

## Co to jest

**pyDpVision** to desktopowa aplikacja do naukowej wizualizacji 3D, rozwijana w IITiS PAN.
Łączy interaktywny renderer OpenGL z obsługą danych medycznych i inżynierskich (chmury punktów, siatki, CT/MRI).
Kod i komentarze częściowo w języku polskim.

---

## Uruchamianie

```
python main.py          # uruchomienie aplikacji
setup.bat               # tworzenie .venv i instalacja zależności
```

PyInstaller spec: `pyDpVision.spec` → `dist/pyDpVision/pyDpVision.exe`

---

## Struktura katalogów

```
main.py                  # punkt wejścia — tworzy QApplication, ładuje pluginy, startuje Qt event loop
dp_testy.py              # tymczasowy moduł deweloperski importowany przy starcie (do usunięcia w produkcji)
dpVision/                # główny pakiet
  globals.py             # singleton AP — globalny locator serwisów
  mainApplication.py     # MainApplication(QApplication) — rejestr pluginów
  workspace.py           # Workspace — korzeń sceny, zarządza renderowaniem 2-pass
  baseObject.py          # BaseObject(QObject) — baza wszystkich obiektów sceny
  object.py              # Object(BaseObject) — dodaje listę dzieci m_data
  pointCloud.py          # PointCloud(Object) — VBO, shadery, tryby renderowania
  mesh.py                # Mesh(PointCloud) — trójkąty, materiały, tekstury
  transform.py           # Transform — węzeł grupujący z transformacją przestrzenną
  volumetric.py          # Volumetric — dane wolumetryczne (CT/MRI)
  annotation.py          # Annotation + podklasy (Sphere/Plane/Point/Path/Triangle/Elipsoide)
  dHJoint.py / dHModel.py # Modele kinematyczne Denavit-Hartenberg
  parser.py              # Parser(QObject) — baza parserów z sygnałami Qt progress
  pluginInterface.py     # PluginInterface(ABC) — baza pluginów
  colormaps.py           # mapy kolorów
  marchingCubes.py       # algorytm marching cubes
  gui/                   # warstwa UI (Qt5 MDI)
  parsers/               # parsery formatów plików
plugins/                 # pluginy zewnętrzne (frasta/, disabled/)
dev/                     # skrypty testowe deweloperskie (nie produkcja)
docs/                    # dokumentacja (LaTeX)
sample_data/             # dane przykładowe (.atmdl, .mtl)
```

---

## Globalny singleton AP (`dpVision/globals.py`)

`AP` to główny locator serwisów — używany wszędzie w kodzie:

| Pole | Typ | Opis |
|---|---|---|
| `AP.mainApp` | `MainApplication` | instancja QApplication, rejestr pluginów |
| `AP.mainWin` | `MainWindow` | główne okno, dostęp do dockwidgetów i widoków GL |
| `AP.settings` | `QSettings` | ustawienia aplikacji |
| `AP.wboit_pass` | `None / -1 / 0 / 1` | aktywny pass renderowania WBOIT |

Pomocnicze: `AP.addObject()`, `AP.removeObject()`, `AP.load()`, `AP.updateAllViews()`, `AP.loadUi()`

---

## Hierarchia klas obiektów sceny

```
BaseObject(QObject)          — label, description, visibility flags, weakref do rodzica
 └── Object                  — lista dzieci m_data, zapytania po typie/etykiecie
      ├── PointCloud          — wierzchołki/kolory/normalne (NumPy), VBO, shadery
      │    └── Mesh           — indeksy trójkątów, materiały, tekstury
      ├── NDimCloud           — chmura N-wymiarowa
      ├── Volumetric          — dane wokseli (CT/MRI + SliceMetadata)
      ├── GridData64          — siatka 2.5D / mapa wysokości
      ├── Image               — obraz 2D
      ├── Transform           — węzeł grupujący + transformacja
      ├── Annotation          — nakładka adnotacyjna
      │    └── AnnotationSphere/Plane/Point/Path/Triangle/Elipsoide
      ├── DHJoint / DHModel   — kinematyka Denavit-Hartenberg
      ├── Motion              — sekwencja animacji
      └── Sphere / SphereGrid — obiekty prymitywne
```

---

## GUI (`dpVision/gui/`)

Qt5 MDI. Pliki `.ui` ładowane dynamicznie przez `AP.loadUi()` (obsługuje tryb dev i PyInstaller).

| Komponent | Opis |
|---|---|
| `MainWindow` | QMainWindow, MDI area, menu plik, akcje |
| `GLViewer` | QOpenGLWidget — viewport 3D z kamerą, obsługuje renderowanie WBOIT multi-pass |
| `MdiChild` | okno MDI owijające GLViewer |
| `DockWidgetWorkspace` | lewy dock: drzewo sceny |
| `DockWidgetProperties` | lewy dock: inspektor właściwości wybranego obiektu |
| `DockWidgetPluginList` | lewy dock: lista załadowanych pluginów |
| `DockWidgetPluginPanel` | lewy dock: panel UI aktywnego pluginu |
| `propMesh`, `propPointCloud`, ... | panele właściwości per typ obiektu |

---

## System pluginów

- **Odkrywanie:** `MainApplication.load_plugins()` skanuje `./plugins/*/pluginMain.py`
- **Interfejs:** klasa dziedziczy `PluginInterface(ABC)`, wymagane: `on_load()`, `on_unload()`, `perform_action()`
- **Aktywny plugin:** `AP.mainApp.activePlugin`
- **Dołączony plugin:** `plugins/frasta/` — analiza powierzchni frędzlowej, własne doki i kontroler
- `plugins/disabled/` — nie jest auto-ładowany

---

## System parserów (`dpVision/parsers/`)

Parsery dziedziczą po `Parser` lub `ThreadedParser`, deklarują `load_exts` / `save_exts`, samorejestrują się w `Parser.parsers`.

| Parser | Format |
|---|---|
| `ParserATMDL` | `.atmdl` (własny format animacji/modelu) |
| `ParserASC` | `.asc` (ASCII chmura punktów) |
| `ParserDICOM` | DICOM (pydicom, SimpleITK) |
| `ParserDPV` | `.dpv` (natywny format projektu) |
| `ParserE57` | `.e57` (pye57, subprocess) |
| `ParserNRRD` | `.nrrd` (dane wolumetryczne) |
| `ParserOBJ` | `.obj` Wavefront |
| `ParserPLY` | `.ply` Stanford |
| `ParserSTL` | `.stl` |
| `ParserCSV` | `.csv` |
| `ParserIMAGE2D` | PNG/JPG/... |

---

## Uwagi DICOM

- `ParserDICOM` sortuje warstwy przede wszystkim według `ImagePositionPatient` oraz `ImageOrientationPatient`, a dopiero później używa `SliceLocation` lub `InstanceNumber`.
- Odstęp między warstwami powinien być wyznaczany z geometrii serii (`ImagePositionPatient`), ponieważ część zestawów nie zawiera `SliceLocation`, `SliceThickness` ani `SpacingBetweenSlices`.
- Parser filtruje pliki wczytywane z katalogu do tej samej `SeriesInstanceUID` co plik startowy, aby nie mieszać kilku serii obecnych w jednym folderze.

---

## Renderowanie WBOIT

Order-Independent Transparency (Weighted Blended):
- `AP.wboit_pass = None` — normalny render (nieprzezroczyste)
- `AP.wboit_pass = 0` — akumulacja wag
- `AP.wboit_pass = 1` — kompozycja
- `AP.wboit_pass = -1` — pass do wyłączenia przezroczystości

Obiekty sprawdzają `AP.wboit_pass` w metodzie `render()`.

---

## Kluczowe zależności

| Pakiet | Zastosowanie |
|---|---|
| `PyQt5` | UI, sygnały, OpenGL widget |
| `PyOpenGL` | bindingi OpenGL |
| `numpy` | tablice wierzchołków, ścian, wolumenów |
| `pydicom`, `SimpleITK` | DICOM / obrazowanie medyczne |
| `pye57` | format E57 |
| `PyMCubes` | marching cubes |
| `opencv-python` | przetwarzanie obrazów |
| `scikit-image/learn`, `scipy` | analiza naukowa |

---

## Wzorce do zapamiętania

1. **`AP` to główny locator** — nie ma injection dependencies, wszystko przez `AP.*`
2. **`.ui` pliki** ładowane dynamicznie — szukaj w `dpVision/gui/forms/`
3. **Parsery samorejestrują się** przez dodanie do `Parser.parsers` przy imporcie
4. **`multiprocessing.freeze_support()`** na początku `main.py` — wymagane dla PyInstaller + E57
5. **Locale `pl_PL.UTF-8`** ustawiane przy starcie (separator dziesiętny: przecinek)
6. **`m_data`** — standardowa nazwa listy dzieci w `Object` i `Workspace`
---

## Slice Preview

- Wolumen ma osobny dialog 2D do przegladania przekrojow `XY`, `YZ` i `ZX`.
- Punkt wejscia w GUI: menu kontekstowe obiektu `Volumetric` -> `volumetric...` -> `slice preview`.
- Logika pobierania przekrojow i projekcji siedzi w `dpVision/volumetric.py`, a sam dialog w `dpVision/gui/dialogVolumetricPreview.py`.
- Aktualna wersja dialogu `slice preview` jest tri-planar: trzy widoki sa zsynchronizowane wspolnym crosshairem oraz klikaniem w panelach.
- Dialog ma tez panel `OBLIQUE`, liczony wokol aktualnego crosshaira na podstawie katow `yaw/pitch`.
- `OBLIQUE` probkuje teraz wolumen w przestrzeni `world/patient`, wykorzystujac osie i spacing zachowane w `SliceMetadata`, a nie tylko indeksy tablicy.
- Uzytkownik moze wybrac osie swiata `X/Y/Z` niezaleznie dla `yaw` i `pitch`, bez zmiany backendowego modelu przekroju.
- Preview obsluguje tez `slab`: grubosc w mm, liczbe probek oraz tryby redukcji `center/mean/max/min` dla widokow ortogonalnych i `OBLIQUE`.
- Tryb `RTG` ma teraz kilka metod projekcji: `mean`, `sum`, `max` oraz `xray` (pseudo-Beer-Lambert).
- Dla `xray` w preview dostepne sa parametry `Xray gain` i `Xray gamma`; wynik `xray` uzywa lagodnej kompresji logarytmicznej oraz robust range z percentyla, zeby zachowac widocznosc slabych struktur bez agresywnego auto-rozciagania.
- Zakres `Xray gain` w GUI jest dostosowany do logarytmicznego modelu `xray`, zeby uzyteczne strojenie nie bylo scisniete przy samym koncu skali.
- Podczas dluzszych przeliczen dialog pokazuje kursor oczekiwania.
- Przelacznik `RTG` dziala per panel (`XY`, `YZ`, `ZX`, `OBLIQUE`), a `RTG all` w gornej belce jest tylko szybkim skrotem do ustawienia wszystkich naraz.
- Dialog preview obsluguje tez przejscie `Quad <-> Full` per panel: checkbox `Full` w naglowku danego widoku wypelnia nim caly obszar preview, a jego wylaczenie wraca do ukladu czterech okien.
- W trybie `Full` dialog przelicza tylko aktualnie widoczny panel, zeby nie spowalniac pracy ukrytymi widokami.
- Panel `OBLIQUE` jest opcjonalny i domyslnie ukryty przez `Show oblique`, zeby ograniczyc koszt najciezszych przeliczen podczas zwyklej pracy na ortogonalnych przekrojach.
- `Volumetric` ma teraz backendowy resampling w przestrzeni swiata: `resample_to_grid(...)` buduje nowy wolumen dla zadanej siatki `origin/basis/spacing/shape`, a `resample_like(other)` pozwala przepisac dane do siatki innego wolumenu.
- Testowo w menu kontekstowym `Volumetric` jest akcja `resample to global grid`: bierze `getGlobalTransformation()` obiektu, pyta o izotropowy voxel i tworzy nowy wolumen osadzony bezposrednio w root workspace. Docelowa siatka jest osiowo wyrownana do globalnego `XYZ`, bo aktualny renderer wolumenu nie rysuje jeszcze poprawnie danych z dowolnie obrocona baza voxeli.

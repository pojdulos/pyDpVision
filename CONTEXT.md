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

Pomocnicze kontrolki:
- `dpVision/gui/multiSpinBox.py` (`MultiSpinBox`, `MultiSpinBoxWithLock`) narzucaja minimalna wysokosc wynikajaca z zawartosci i ustawiają stala polityke pionowa, zeby layout rodzica nie mogl ich zgniatac do zera.
- `dpVision/gui/flowLayout.py` udostepnia wielokrotnego uzytku `FlowLayout`, ktory uklada widgety od lewej do prawej i automatycznie zawija je do kolejnego wiersza, gdy dock lub panel zrobi sie zbyt waski.
- `PropTransform` uzywa `FlowLayout` w parach edytorow i nie powinien juz ograniczac grupy `Transformation` sztywnym maksimum szerokosci; sekcje maja moc rozszerzac sie do szerokosci docka i zawijac dopiero przy braku miejsca.
- Panele w `DockWidgetProperties` powinny opierac rozmiar na `sizeHint`/`minimumSizeHint` i normalnym relayoutcie Qt; nie nalezy zamrazac ich wysokosci jednorazowym `setMinimumHeight(...)`, bo psuje to rozwijane sekcje i przewijanie `QScrollArea`.
- W panelach opartych o `QFormLayout` pola edycyjne powinny zwykle zostawac przy `sizeHint()` (`FieldsStayAtSizeHint` + kompaktowy `QSizePolicy`), zamiast rozciagac sie na cala szerokosc docka.
- Jesli panel ma pozostac kompaktowy, takze zwykle `QGroupBox` w kartach powinny miec uklad wyrównany do lewej i polityke rozmiaru oparta o zawartosc, zamiast wymuszac pelna szerokosc kontenera.
- W `propVirtualXRay` naglowki sekcji rozwijanych sa kompaktowe, a akcje w zakladce `Run` sa ukladane pionowo; etykiety statusu powinny miec wlaczone zawijanie linii.

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
- Jest tez wariant `resample_like_global(...)`, ktory uwzglednia `getGlobalTransformation()` obu wolumenow i pozwala przepisac jeden wolumen dokladnie do siatki drugiego.
- Backend ma tez metody laczenia wolumenow po wspolnym resamplingu: `merge_to_grid_global(...)` oraz `merge_like_global(...)`. Obsluguja polityki konfliktow `max`, `min`, `mean`, `sum`, `overwrite` i `first_non_empty`, korzystajac z mask waznosci probek zamiast zgadywania po samym `fill_value`.
- Dla pracy na wielu tomografiach backend umie tez wyznaczyc wspolna siatke: `compute_common_grid_global(...)` obsluguje polityki `reference`, `finest`, `coarsest` i `manual`, a `merge_to_common_grid_global(...)` scala wolumeny po automatycznym doborze takiej siatki.
- Osobny backend RTG jest wydzielany do `dpVision/xrayProjection.py`. Na start zawiera klasy `XRayProjectionGeometry`, `XRayPhysicsModel`, `XRaySampleSource`, `VolumetricXRaySource` i `XRayProjector`, zeby rozwijac geometrie i fizyke projekcji niezaleznie od klasy `Volumetric`.
- Backend RTG ma teraz tez wyzszy poziom API: `XRayProjectionGeometry.from_detector_pose(...)` do wygodniejszego budowania geometrii, `XRayProjectionQualityProfile` z presetami `draft/normal/high`, `XRayProjectionConfig` do spinania geometrii, fizyki i prezentacji oraz `XRayScene` jako kontener zrodel i wygodny punkt wejscia do projekcji.
- Nad surowym wynikiem projekcji jest tez osobna warstwa prezentacji: `XRayPresentationModel`, `RawPresentationModel`, `FilmLikePresentationModel` i `DigitalRadiographyPresentationModel`. Pozwala to rozwijac wyglad obrazu RTG bez ruszania samego projektora.
- `XRayProjector.project(..., return_stats=True)` potrafi teraz zwrocic tez `XRayProjectionStats`, czyli podstawowe statystyki czasu, liczby promieni i liczby probek.
- Integracja z drzewem sceny zaczyna sie od nowego obiektu `VirtualXRay` w `dpVision/virtualXRay.py`. To zwykly `Object`, ktory rysuje gizmo zrodla i detektora, zbiera potomne wolumeny z istniejacej hierarchii sceny i buduje z nich `XRayScene` oraz `XRayProjectionConfig`.
- `VirtualXRay` pracuje w lokalnym ukladzie odniesienia zwiazanym z samym obiektem: geometria zrodla i detektora jest opisana lokalnie, a potomne wolumeny sa przekladane do tego ukladu przez transformacje wzgledne wobec `VirtualXRay`, nie przez absolutne wspolrzedne globalne.
- `VirtualXRay` ma juz tez prosty panel wlasciwosci w `dpVision/gui/propVirtualXRay.py`, podpiety w `DockWidgetProperties`. Pozwala edytowac tryb `cone/parallel`, pozycje i orientacje detektora, pozycje zrodla lub kierunek promieni, rozdzielczosc detektora, wielkosc piksela, `step_mm` i profil jakosci.
- Z tego samego panelu mozna tez uruchomic symulacje przez przycisk `Run Simulation`: projekcja jest liczona z bieżących ustawien `VirtualXRay`, a wynik trafia do workspace jako zwykly obiekt `Image`. Panel pokazuje tez podstawowe statystyki czasu i liczby probek.
- Panel `VirtualXRay` jest teraz podzielony na zakladki `Scene`, `Detector`, `Source`, `Sampling` i `Run`, zeby nie pokazywac wszystkich parametrow naraz.
- Panel `VirtualXRay` ma tez osobna zakladke `Presentation`, gdzie da sie stroic sposob generowania obrazu koncowego (`digital / film / raw`, `invert`, `gamma`, `contrast`, `robust percentile`, opcjonalne `window center/width`). Dla trybow prezentacyjnych wynik jest przy zamianie na `Image` mapowany w stalym zakresie `0..1`, zeby unikac dodatkowego prześwietlania przez wtorny auto-stretch.
- Ten backend ma tez helpery eksportu wyniku projekcji: `normalize_projection_to_uint8(...)`, `normalize_projection_to_uint16(...)`, `save_projection_png(...)`, `save_projection_tiff(...)` i `save_projection_dicom(...)`. DICOM jest na razie zapisywany jako prosty `Secondary Capture`.
- W `docs/xray_projection.tex` jest osobna dokumentacja LaTeX calego modulu `xrayProjection`, z opisem architektury, wzorami dla geometrii i akwizycji, schematami TikZ oraz rozdzialem o zlozonosci obliczeniowej i kompromisach parametrow detektora oraz `step_mm`.
- W `dp_testy.py` sa tez pomocnicze scenariusze `create_synthetic_xray_demo_dicoms()` i `demo_synthetic_xray_projection()`, ktore buduja dwa proste syntetyczne zestawy DICOM (czaszka i zuchwa) oraz pokazuja podstawowe uzycie backendu RTG przez `XRayScene` i `XRayProjectionConfig`, z rozdzieleniem na surowy wynik projekcji, obraz po modelu prezentacji cyfrowego RTG oraz statystyki projekcji.
- W `dp_testy.py` jest tez helper `create_virtual_xray_demo_object()`, ktory tworzy przykładowy obiekt `VirtualXRay` z potomnymi transformacjami dla syntetycznej czaszki i zuchwy.
- Testowo w menu kontekstowym `Volumetric` jest akcja `resample to global grid`: bierze `getGlobalTransformation()` obiektu, pyta o izotropowy voxel i tworzy nowy wolumen osadzony bezposrednio w root workspace. Docelowa siatka jest osiowo wyrownana do globalnego `XYZ`, bo aktualny renderer wolumenu nie rysuje jeszcze poprawnie danych z dowolnie obrocona baza voxeli.
- W menu `Volumetric` jest tez testowa akcja `resample to another volume grid`, ktora wybiera drugi wolumen z workspace i tworzy wynik w dokladnie tej samej siatce voxeli, pod tym samym rodzicem co wolumen docelowy.
- Dalsze RTG: `XRayPhysicsModel` obsluguje teraz rozne tryby okna materialowego (`hard`, `linear`, `sigmoid`) z parametrem `material_window_softness`, zeby ograniczac material na wejsciu bez brutalnego wycinania cienkich struktur.
- Dalsze RTG: w panelu `VirtualXRay` zakladka `Physics` steruje oknem materialowym na etapie `scalar -> mu`, a zakladka `Presentation` steruje tylko obrazem koncowym po projekcji.
- RTG — flaga trybu: `VirtualXRay` ma teraz jawne pole `projection_mode = "cone" | "parallel"` zamiast opierania sie na `source_position_ref is not None`. Oba pola (`source_position_ref` i `ray_direction_ref`) sa zawsze zainicjalizowane; `build_geometry()` przekazuje `None` dla nieaktywnego parametru dopiero przy budowaniu `XRayProjectionGeometry`. `getLocalBB()`, `renderSelf()` i `info()` uzywaja flagi zamiast sprawdzania `None`. Panel GUI `on_mode_changed` tylko ustawia `obj.projection_mode`, bez zerowania ani przechowywania wartosci.
- RTG — cache projekcji: `VirtualXRay` przechowuje teraz `last_raw_projection` (float32 ndarray lub `None`). Nowa metoda `project_and_cache()` liczy projekcje i zapisuje surowy wynik w cache; `apply_presentation()` stosuje biezacy model prezentacji do cache bez ponownego ray-marchingu. Panel `Run` ma drugi przycisk `Update display`, aktywny tylko gdy cache istnieje — pozwala strojic kontrast/gamma/okno bez ponownej pelnej symulacji. `on_run_simulation` uzywa teraz `project_and_cache()` zamiast `render_projection()`.
- Dalsze RTG: przy przejsciu `cone -> parallel` panel `VirtualXRay` ustawia domyslny kierunek promieni przeciwny do normalnej detektora, zeby projekcja rownolegla nie startowala w zla strone i nie dawala pustego obrazu.
- Dalsze RTG: gizmo `VirtualXRay` ma teraz subtelniejsze kolory i delikatne osie lokalne, z osobnym kolorem wypelnienia i ramki detektora, cieplejszym oznaczeniem zrodla oraz dyskretnym polaczeniem z centrum detektora.
- Dalsze RTG: dla trybu `cone` gizmo rysuje teraz cienkie linie od zrodla do naroznikow detektora, zeby bylo widac pole widzenia ukladu.
- Dalsze RTG: panel `VirtualXRay` ma teraz tez zakladke `Advanced`, ktora wystawia do szybkich testow nizszy poziom parametrow backendu, m.in. `mu_air`, `mu_water`, `hounsfield_air`, `attenuation_scale`, `output_mode`, `intensity_floor`, `source_interpolation` i opcjonalny `source_fill_value`.
- GUI: kontener `PropWidget.build(...)` nie blokuje juz szerokosci paneli wlasciwosci do poczatkowego `sizeHint()`. Panele, w tym `VirtualXRay`, powinny teraz rozszerzac sie poziomo wraz z dockiem `Properties`.

## RTG - stan biezacy

- Ten blok opisuje aktualny stan backendu i GUI RTG i ma pierwszenstwo interpretacyjne nad starszymi punktami powyzej, jesli sa z nimi niespojne.
- `XRayProjector` jest juz wektoryzowany po promieniach i przyjmuje `progress_callback`, a `XRayScene.project(...)` oraz `XRayScene.render(...)` przekazuja ten callback dalej.
- `XRayPhysicsModel` ma obecnie parametry: `mu_air`, `mu_water`, `hounsfield_air`, `attenuation_scale`, `output_mode`, `intensity_floor`, `material_window_center`, `material_window_width`, `material_window_mode` oraz `material_window_softness`.
- `XRayPhysicsModel` ma obecnie parametry: `mu_air`, `mu_water`, `hounsfield_air`, `attenuation_scale`, `output_mode`, `intensity_floor`, `material_response_mode`, `bone_threshold_hu`, `bone_threshold_softness`, `material_window_center`, `material_window_width`, `material_window_mode` oraz `material_window_softness`.
- Okno materialowe dziala na etapie `scalar -> mu`, czyli przed projekcja. Obsluguje tryby `hard`, `linear` i `sigmoid`.
- Bazowy model `HU -> mu` jest teraz przelaczany przez `material_response_mode`:
- `linear`
- `piecewise_bone`
- `piecewise_soft_tissue`
- `bone_threshold`
- `piecewise_bone` i `piecewise_soft_tissue` sa prostymi krzywymi odcinkowymi przygotowanymi do szybkiego porownania jakościowego bez dalszego strojenia kodu.
- `bone_threshold` miesza model neutralny z modelem kostnym powyzej miekkiego progu HU i lepiej pasuje do projekcji niz heurystyka pelnego okna z segmentacji powierzchni.
- Zakladka `Presentation` ma teraz tez szybkie presety wygladu (`balanced`, `bone_soft`, `bone_contrast`, `film_soft`), ktore jednoczesnie ustawiaja tryb prezentacji, `gamma`, `contrast` i `robust percentile` bez zmiany modelu fizycznego.
- `VirtualXRay` ma teraz backendowa estymacje progu kosci na podstawie heurystyki z `marchingCubes.py`: metoda `estimate_bone_threshold()` uzywa gradientowego `mc_estimate_threshold(...)`, a `apply_estimated_bone_threshold()` ustawia tryb `bone_threshold`, wpisuje prog HU i czysci pelne okno materialowe. Panel `Physics` ma do tego przycisk `Auto bone threshold`.
- `VirtualXRay` ma jawne pole `projection_mode = "cone" | "parallel"`. Nie opiera juz logiki trybu na `source_position_ref is None`.
- Presety geometrii `VirtualXRay` sa teraz ladowane z pliku `dpVision/presets/xray_geometry_presets.json`, a definicje zaszyte w `virtualXRay.py` zostaly tylko jako fallback awaryjny. Zakladka `Geometry` nadal ma szybki wybor `Preset` + `Apply`, ale nowe modele geometrii mozna dodawac bez zmiany kodu.
- `VirtualXRay` przechowuje `last_raw_projection` i udostepnia:
- `project_and_cache(...)`: liczy surowa projekcje i zapisuje ja do cache.
- `apply_presentation()`: stosuje biezacy model prezentacji do cache bez ponownego ray-marchingu.
- `build_geometry()` przekazuje do `XRayProjectionGeometry` tylko aktywny parametr geometrii: `source_position_ref` dla `cone` albo `ray_direction_ref` dla `parallel`.
- `VirtualXRay` nadal pracuje w lokalnym ukladzie odniesienia obiektu i zbiera potomne `Volumetric` przez istniejace mechanizmy drzewa sceny, przeliczajac transformacje wzgledem siebie.
- Panel `PropVirtualXRay` jest aktualnie zorganizowany jako zakladki:
- `Geometry`
- `Physics`
- `Presentation`
- `Run`
- W zakladkach `Geometry` i `Physics` sa checkboxy `Show advanced`, ktore odslaniaja nizszy poziom parametrow backendu.
- Zakladka `Run` ma obecnie przyciski:
- `Refresh`
- `Run Simulation`
- `Update display`
- `Run Simulation` liczy projekcje i aktualizuje cache.
- `Update display` przelicza tylko warstwe prezentacji na bazie `last_raw_projection`, bez ponownego ray-marchingu.
- Przy przejsciu `cone -> parallel` GUI ustawia domyslny kierunek promieni zgodny z `detector_normal_ref`, zeby projekcja rownolegla nie startowala w zla strone.
- Gizmo `VirtualXRay` ma subtelniejsze kolory, lokalne osie i dla `cone` cienkie linie od zrodla do naroznikow detektora, pokazujace pole widzenia.

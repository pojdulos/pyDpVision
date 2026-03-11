#version 330 core

// --- Uniformy: Macierz MVP ---
uniform mat4 u_mvp;

// --- Rozmiar siatki ---
uniform int u_width;    // liczba kolumn (azymut)
uniform int u_height;   // liczba wierszy (elewacja)

// --- Zakresy kątowe (stopnie) ---
uniform float u_az_min;   // minimalny azymut [°]
uniform float u_d_az;     // krok azymutu na kolumnę [°/px]
uniform float u_el_min;   // minimalna elewacja [°]
uniform float u_d_el;     // krok elewacji na wiersz [°/px]

// --- Punkt odniesienia (origin skanera) ---
uniform vec3 u_origin;

// --- Tekstura RGBA32F: R=zasięg, G=intensywność, B=0, A=maska ---
uniform sampler2D u_gridTex;

// --- Wyjście do fragment shadera ---
out float v_range;
out float v_intensity;
out float v_mask;

const float PI = 3.14159265358979323846;

void main()
{
    // Indeks → wiersz i, kolumna j (wiersz = elewacja, kolumna = azymut)
    int idx = gl_VertexID;
    int i = idx / u_width;   // wiersz (elewacja)
    int j = idx % u_width;   // kolumna (azymut)

    // Współrzędne tekstury (środki tekseli — dokładniejsze próbkowanie)
    vec2 texCoord = vec2(
        (float(j) + 0.5) / float(u_width),
        (float(i) + 0.5) / float(u_height)
    );

    vec4 data = texture(u_gridTex, texCoord);
    float r         = data.r;   // zasięg
    v_intensity     = data.g;   // intensywność odbicia
    v_mask          = data.a;   // maska ważności
    v_range         = r;

    // Kąty azymutu i elewacji dla środka piksela [stopnie → radiany]
    float az_deg = u_az_min + (float(j) + 0.5) * u_d_az;
    float el_deg = u_el_min + (float(i) + 0.5) * u_d_el;
    float az = az_deg * PI / 180.0;
    float el = el_deg * PI / 180.0;

    // Konwersja sferyczna → kartezjańska
    // Az 0° = +X, Az 90° = +Y, El 0° = poziom, El +90° = zenit
    float cos_el = cos(el);
    float x = r * cos_el * cos(az) + u_origin.x;
    float y = r * cos_el * sin(az) + u_origin.y;
    float z = r * sin(el)          + u_origin.z;

    gl_Position = u_mvp * vec4(x, y, z, 1.0);
}

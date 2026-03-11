#version 330 core

// --- Zakres wartości dla colormapy ---
uniform float u_minVal;        // min zasięgu lub intensywności
uniform float u_maxVal;        // max zasięgu lub intensywności

// --- Tryb koloru ---
uniform bool  u_useUniformColor;   // jeśli true → jednolity kolor
uniform vec3  u_uniformColor;      // jednolity kolor (RGB)
uniform bool  u_colorByIntensity;  // jeśli true → koloruj wg intensywności, wpp wg zasięgu

// --- Paleta kolorów (1D LUT, 256×1 px) ---
uniform sampler2D u_palette;

// --- Dane z vertex shadera ---
in float v_range;
in float v_intensity;
in float v_mask;

out vec4 fragColor;

void main()
{
    // Odrzuć nieważne piksele (brak echa)
    if (v_mask < 0.5)
        discard;

    vec3 color;
    if (u_useUniformColor) {
        color = u_uniformColor;
    } else {
        float val = u_colorByIntensity ? v_intensity : v_range;
        float t = clamp((val - u_minVal) / (u_maxVal - u_minVal), 0.0, 1.0);
        color = texture(u_palette, vec2(t, 0.5)).rgb;
    }

    fragColor = vec4(color, 1.0);
}

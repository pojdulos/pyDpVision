#version 330 core

// --- Zakres wartości dla colormapy ---
uniform float u_minVal;
uniform float u_maxVal;

// --- Tryb koloru ---
// 0 = RGB, 1 = INTENSITY, 2 = GREYSCALE, 3 = RANGE_COLOR, 4 = UNIFORM
uniform int   u_mode;
uniform vec3  u_uniformColor;
uniform bool  u_hasRgb;          // czy VBO zawiera dane RGB
uniform bool  u_hasInten;        // czy VBO zawiera dane intensywności

// --- Paleta kolorów (1D LUT 256×1 px) ---
uniform sampler2D u_palette;

// --- Dane z vertex shadera ---
in float v_range;
in float v_intensity;
in float v_mask;
in vec3  v_rgb;

out vec4 fragColor;

void main()
{
    if (v_mask < 0.5)
        discard;

    vec3 color;

    if (u_mode == 4) {                          // UNIFORM
        color = u_uniformColor;
    } else if (u_mode == 0 && u_hasRgb) {      // RGB
        color = v_rgb;
    } else if (u_mode == 1 && u_hasInten) {    // INTENSITY
        float t = clamp((v_intensity - u_minVal) / (u_maxVal - u_minVal + 1e-9), 0.0, 1.0);
        color = texture(u_palette, vec2(t, 0.5)).rgb;
    } else if (u_mode == 2) {                   // GREYSCALE
        float lum;
        if (u_hasRgb)
            lum = dot(v_rgb, vec3(0.299, 0.587, 0.114));
        else if (u_hasInten)
            lum = clamp((v_intensity - u_minVal) / (u_maxVal - u_minVal + 1e-9), 0.0, 1.0);
        else
            lum = clamp((v_range    - u_minVal) / (u_maxVal - u_minVal + 1e-9), 0.0, 1.0);
        color = vec3(lum);
    } else {                                    // RANGE_COLOR (mode==3) lub fallback
        float t = clamp((v_range - u_minVal) / (u_maxVal - u_minVal + 1e-9), 0.0, 1.0);
        color = texture(u_palette, vec2(t, 0.5)).rgb;
    }

    fragColor = vec4(color, 1.0);
}


#version 330 core

// --- Zakres wartości dla colormapy ---
uniform float u_minVal;
uniform float u_maxVal;

// --- Tryb koloru: 0=RGB,1=INTENSITY,2=GREYSCALE,3=RANGE_COLOR,4=UNIFORM ---
uniform int   u_mode;
uniform vec3  u_uniformColor;
uniform bool  u_hasInten;

// --- Paleta kolorów (1D LUT, 256×1 px) ---
uniform sampler2D u_palette;

// --- Dane z vertex shadera ---
in float v_range;
in float v_intensity;
in float v_mask;

out vec4 fragColor;

void main()
{
    if (v_mask < 0.5)
        discard;

    vec3 color;
    if (u_mode == 4) {
        color = u_uniformColor;
    } else if (u_mode == 1 && u_hasInten) {
        float t = clamp((v_intensity - u_minVal) / (u_maxVal - u_minVal), 0.0, 1.0);
        color = texture(u_palette, vec2(t, 0.5)).rgb;
    } else if (u_mode == 2) {
        float grey = u_hasInten
            ? clamp((v_intensity - u_minVal) / (u_maxVal - u_minVal), 0.0, 1.0)
            : clamp((v_range     - u_minVal) / (u_maxVal - u_minVal), 0.0, 1.0);
        color = vec3(grey);
    } else {
        // RANGE_COLOR (mode==3) lub fallback
        float t = clamp((v_range - u_minVal) / (u_maxVal - u_minVal), 0.0, 1.0);
        color = texture(u_palette, vec2(t, 0.5)).rgb;
    }

    fragColor = vec4(color, 1.0);
}

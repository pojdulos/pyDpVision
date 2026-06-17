#version 330 core

uniform float u_minVal;
uniform float u_maxVal;
uniform int   u_color_mode;
uniform vec3  u_uniformColor;
uniform bool  u_hasRgb;
uniform bool  u_hasInten;
uniform sampler2D u_palette;
uniform int u_wboit_pass;

in float v_range;
in float v_intensity;
in vec3  v_rgb;

layout(location = 0) out vec4 out0;

void main()
{
    vec2 uv = gl_PointCoord * 2.0 - 1.0;
    float r2 = dot(uv, uv);
    float alpha = exp(-r2 * 0.5);
    if (alpha < 0.01) discard;

    vec3 color;
    if (u_color_mode == 4) {
        color = u_uniformColor;
    } else if (u_color_mode == 0 && u_hasRgb) {
        color = v_rgb;
    } else if (u_color_mode == 1 && u_hasInten) {
        float t = clamp((v_intensity - u_minVal) / (u_maxVal - u_minVal + 1e-9), 0.0, 1.0);
        color = texture(u_palette, vec2(t, 0.5)).rgb;
    } else if (u_color_mode == 2) {
        float lum;
        if (u_hasRgb)
            lum = dot(v_rgb, vec3(0.299, 0.587, 0.114));
        else if (u_hasInten)
            lum = clamp((v_intensity - u_minVal) / (u_maxVal - u_minVal + 1e-9), 0.0, 1.0);
        else
            lum = clamp((v_range - u_minVal) / (u_maxVal - u_minVal + 1e-9), 0.0, 1.0);
        color = vec3(lum);
    } else {
        float t = clamp((v_range - u_minVal) / (u_maxVal - u_minVal + 1e-9), 0.0, 1.0);
        color = texture(u_palette, vec2(t, 0.5)).rgb;
    }

    if (u_wboit_pass == 0) {
        out0 = vec4(color * alpha, alpha);
    } else {
        out0 = vec4(alpha, 0.0, 0.0, 0.0);
    }
}

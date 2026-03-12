#version 330 core

// --- Pre-baked VBO (x, y, z, range, intensity, r, g, b) ---
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec2 a_values;   // x = zasięg, y = intensywność
layout(location = 2) in vec3 a_rgb;      // 0.0–1.0

uniform mat4 u_mvp;

out float v_range;
out float v_intensity;
out float v_mask;       // zawsze 1.0 — VBO zawiera tylko ważne punkty
out vec3  v_rgb;

void main()
{
    gl_Position = u_mvp * vec4(a_position, 1.0);
    v_range     = a_values.x;
    v_intensity = a_values.y;
    v_mask      = 1.0;
    v_rgb       = a_rgb;
}

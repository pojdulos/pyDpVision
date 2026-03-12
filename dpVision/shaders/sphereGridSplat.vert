#version 330 core

layout(location = 0) in vec3  a_position;
layout(location = 1) in vec2  a_values;   // x = range [m], y = intensity
layout(location = 2) in vec3  a_rgb;

uniform mat4  u_mvp;
uniform mat4  u_mv;
uniform float u_ang_step_rad;
uniform float u_splat_scale;
uniform float u_focal_y;
uniform float u_viewport_h;

out float v_range;
out float v_intensity;
out vec3  v_rgb;

void main()
{
    gl_Position = u_mvp * vec4(a_position, 1.0);

    v_range     = a_values.x;
    v_intensity = a_values.y;
    v_rgb       = a_rgb;

    // eye-space Z for perspective-correct splat size
    vec4 eye_pos = u_mv * vec4(a_position, 1.0);
    float depth  = max(-eye_pos.z, 0.001);

    float world_radius = a_values.x * u_ang_step_rad * u_splat_scale;
    float size_px = u_focal_y * u_viewport_h * 0.5 * (2.0 * world_radius) / depth;
    gl_PointSize = clamp(size_px, 1.0, 200.0);
}


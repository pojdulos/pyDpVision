#version 330 core

layout(location = 0) in vec3 a_position;
layout(location = 1) in vec4 a_color;

uniform mat4 u_mvp;
uniform mat4 u_mv;
uniform mat4 u_projection;
uniform float u_focal_y;
uniform float u_viewport_h;
uniform float u_splat_scale;
uniform float u_point_spacing;
uniform bool u_use_u_color;
uniform vec4 u_color;

out vec4 v_color;

void main()
{
    gl_Position = u_mvp * vec4(a_position, 1.0);
    v_color = u_use_u_color ? u_color : a_color;

    vec4 eye_pos = u_mv * vec4(a_position, 1.0);
    float world_radius = 0.5 * u_point_spacing * u_splat_scale;

    float size_px;
    if (u_projection[3][3] == 0.0)
    {
        float depth = max(-eye_pos.z, 0.001);
        size_px = u_focal_y * u_viewport_h * 0.5 * (2.0 * world_radius) / depth;
    }
    else
    {
        size_px = u_focal_y * u_viewport_h * 0.5 * (2.0 * world_radius);
    }

    gl_PointSize = clamp(size_px, 1.0, 200.0);
}

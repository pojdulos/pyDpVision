#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_color;

out vec3 v_color;

uniform mat4 u_mvp; // Model-View-Projection matrix
uniform vec3 u_color;  // stały kolor z CPU
uniform bool u_use_u_color;

void main()
{
    gl_Position = u_mvp * vec4(a_position, 1.0);
    
    if (u_use_u_color)
        v_color = u_color;
    else
        v_color = a_color;
}

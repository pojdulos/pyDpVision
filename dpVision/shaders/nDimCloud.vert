#version 330 core
layout(location = 0) in vec3 a_position;
layout(location = 1) in vec3 a_color;

out vec3 v_color;

uniform mat4 u_mvp; // Model-View-Projection matrix

void main()
{
    gl_Position = u_mvp * vec4(a_position, 1.0);
    v_color = vec3(0.5,0.5,0.5); //a_color;
}

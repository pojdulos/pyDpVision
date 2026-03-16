#version 330 core

uniform vec4 u_color;
uniform int u_wboit_pass;

layout(location = 0) out vec4 out0;

void main()
{
    float alpha = u_color.a;
    if (alpha < 0.01) {
        discard;
    }

    if (u_wboit_pass == 0) {
        out0 = vec4(u_color.rgb * alpha, alpha);
    } else {
        out0 = vec4(alpha, 0.0, 0.0, 0.0);
    }
}

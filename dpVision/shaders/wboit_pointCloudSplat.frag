#version 330 core

in vec4 v_color;

uniform int u_wboit_pass;

layout(location = 0) out vec4 out0;

void main()
{
    vec2 uv = gl_PointCoord * 2.0 - 1.0;
    float r2 = dot(uv, uv);
    float alpha = v_color.a * exp(-r2 * 2.0);

    if (alpha < 0.01)
        discard;

    if (u_wboit_pass == 0) {
        out0 = vec4(v_color.rgb * alpha, alpha);
    } else {
        out0 = vec4(alpha, 0.0, 0.0, 0.0);
    }
}

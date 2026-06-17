#version 330 core

in vec4 v_color;
out vec4 fragColor;

void main()
{
    vec2 uv = gl_PointCoord * 2.0 - 1.0;
    float r2 = dot(uv, uv);
    float alpha = exp(-r2 * 2.0);

    if (alpha < 0.01)
        discard;

    fragColor = vec4(v_color.rgb, v_color.a * alpha);
}

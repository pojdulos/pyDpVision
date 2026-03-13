#version 330 core
// Weighted Blended OIT – fragment shader for Gaussian Splats (Volumetric)
// pass_idx 0 = accum (blend GL_ONE/GL_ONE)
// pass_idx 1 = reveal (blend GL_ZERO/GL_ONE_MINUS_SRC_COLOR)

uniform vec3 u_tint;
uniform int  u_wboit_pass;

in vec3  v_color;
in float v_valid;

layout(location = 0) out vec4 out0;

void main()
{
    if (v_valid < 0.5) discard;

    vec2  uv    = gl_PointCoord * 2.0 - 1.0;
    float r2    = dot(uv, uv);
    float alpha = exp(-r2 * 2.0);

    if (alpha < 0.01) discard;

    vec3 color = v_color * u_tint;

    float z = gl_FragCoord.z;
    float w = max(1e-2, min(3e3, 10.0 /
        (1e-5 + pow(z * 5.0, 2.0) + pow(z * 200.0, 6.0))));

    if (u_wboit_pass == 0) {
        // Accum pass
        out0 = vec4(color * alpha, alpha) * w;
    } else {
        // Reveal pass
        out0 = vec4(alpha, alpha, alpha, alpha);
    }
}

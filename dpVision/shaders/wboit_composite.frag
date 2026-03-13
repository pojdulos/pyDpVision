#version 330 core
// Weighted Blended OIT – composite pass.
// Blends accumulated transparent layers over the opaque background.
// Output is blended with GL_SRC_ALPHA / GL_ONE_MINUS_SRC_ALPHA.

uniform sampler2D u_accum;   // RGBA32F  – weighted color accumulation
uniform sampler2D u_reveal;  // RGBA8    – product of (1 - alpha_i)

in  vec2 vTexCoord;
out vec4 fragColor;

void main()
{
    vec4  accum  = texture(u_accum,  vTexCoord);
    float reveal = texture(u_reveal, vTexCoord).r;

    // Skip fully empty pixels
    if (abs(accum.a) < 1e-4) discard;

    vec3 avg_color = accum.rgb / accum.a;
    // (1 - reveal) = total coverage of all transparent layers in this pixel
    fragColor = vec4(avg_color, 1.0 - reveal);
}

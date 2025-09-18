#version 330 core
uniform float u_minZ;
uniform float u_maxZ;
uniform bool u_useUniformColor;
uniform vec3 u_uniformColor;

in float v_z;
in float v_mask;
in vec3 v_normal;

out vec4 fragColor;

void main()
{
    if (v_mask < 0.5)
        discard;

    // światło = headlight
    vec3 lightDir = normalize(vec3(0.0, 0.0, 1.0));
    float diff = max(dot(normalize(v_normal), lightDir), 0.2);

    vec3 baseColor;
    if (u_useUniformColor) {
        baseColor = u_uniformColor;
    } else {
        float t = clamp((v_z - u_minZ) / (u_maxZ - u_minZ), 0.0, 1.0);
        baseColor = mix(vec3(1.0, 0.0, 0.0),
                        vec3(0.0, 1.0, 0.0), t);
    }

    fragColor = vec4(baseColor * diff, 1.0);
}

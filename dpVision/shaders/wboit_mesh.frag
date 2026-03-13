#version 330 core
// Weighted Blended OIT – fragment shader for Mesh
// pass_idx 0 = accum (blend GL_ONE/GL_ONE)
// pass_idx 1 = reveal (blend GL_ZERO/GL_ONE_MINUS_SRC_COLOR)

in vec3 smoothVertexNormal;
flat in vec3 flatVertexNormal;
in vec4 vertexColor;
in vec2 TexCoord;
in vec3 FragPos;

uniform sampler2D texture1;
uniform vec4      myColor;        // .a = alpha materia\u0142u
uniform bool useTexture;
uniform bool useFlatShading;
uniform int  u_wboit_pass;

layout(location = 0) out vec4 out0;

void main()
{
    vec3 lightPos = vec3(0.0, 100.0, 600.0);
    vec3 viewPos  = vec3(0.0, 0.0, 200.0);
    vec3 lightColor = vec3(1.0);
    float ambientStrength  = 0.6;
    float specularStrength = 0.5;
    float shininess        = 32.0;

    vec3 norm     = normalize(useFlatShading ? flatVertexNormal : smoothVertexNormal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff    = max(dot(norm, lightDir), 0.0);
    vec3 diffuse  = diff * lightColor;

    vec3 viewDir    = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec      = pow(max(dot(viewDir, reflectDir), 0.0), shininess);
    vec3 specular   = specularStrength * spec * lightColor;

    vec3  result = (ambientStrength * lightColor + diffuse + specular) * vertexColor.rgb;
    // Łączymy alpha z koloru wierzchołka z alpha materiału (myColor.a).
    // Gdy useVColors=true, per-vertex alpha zazwyczaj = 1.0, więc bez tego
    // mnożenia mesh wyglądałby na w pełni nieprzezroczysty mimo ustawienia
    // przezroczystości materiału.
    float alpha  = vertexColor.a * myColor.a;

    if (useTexture) {
        vec4 texColor = texture(texture1, TexCoord);
        result *= texColor.rgb;
        alpha  *= texColor.a;
    }

    if (alpha < 0.01) discard;

    // WBOIT weight: strong near-surface emphasis, robust across depth ranges
    float z = gl_FragCoord.z;
    float w = max(1e-2, min(3e3, 10.0 /
        (1e-5 + pow(z * 5.0, 2.0) + pow(z * 200.0, 6.0))));

    if (u_wboit_pass == 0) {
        // Accum pass: additive blend (GL_ONE, GL_ONE)
        out0 = vec4(result * alpha, alpha) * w;
    } else {
        // Reveal pass: multiplicative blend (GL_ZERO, GL_ONE_MINUS_SRC_COLOR)
        out0 = vec4(alpha, alpha, alpha, alpha);
    }
}

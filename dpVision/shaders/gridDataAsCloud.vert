#version 330 core
uniform mat4 u_mvp;
uniform float u_stepX;
uniform float u_stepY;
uniform float u_offsetX;
uniform float u_offsetY;
uniform int u_width;
uniform int u_height;
uniform sampler2D u_gridTex;

out float v_z;
out float v_mask;
out vec3 v_normal;

void main()
{
    int idx = gl_VertexID;
    int i = idx / u_width;
    int j = idx % u_width;

    vec2 texCoord = vec2(float(j) / float(u_width),
                         float(i) / float(u_height));

    vec2 rg = texture(u_gridTex, texCoord).rg;
    float z = rg.r;
    float mask = rg.g;

    v_z = z;
    v_mask = mask;

    // gradient -> normalna
    float z_left  = texture(u_gridTex, texCoord + vec2(-1.0/u_width, 0)).r;
    float z_right = texture(u_gridTex, texCoord + vec2( 1.0/u_width, 0)).r;
    float z_down  = texture(u_gridTex, texCoord + vec2(0, -1.0/u_height)).r;
    float z_up    = texture(u_gridTex, texCoord + vec2(0,  1.0/u_height)).r;

    float dzdx = (z_right - z_left) / (2.0 * u_stepX);
    float dzdy = (z_up - z_down) / (2.0 * u_stepY);

    v_normal = normalize(vec3(-dzdx, -dzdy, 1.0));

    float x = u_offsetX + j * u_stepX;
    float y = u_offsetY + i * u_stepY;

    gl_Position = u_mvp * vec4(x, y, z, 1.0);
}

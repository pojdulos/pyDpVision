#version 330 core
layout(points) in;
layout(triangle_strip, max_vertices = 4) out;

uniform mat4 u_mvp;
uniform float u_stepX;
uniform float u_stepY;
uniform float u_offsetX;
uniform float u_offsetY;
uniform int u_width;
uniform int u_height;
uniform sampler2D u_gridTex;

in ivec2 v_idx[];
out float v_z;
out float v_mask;
out vec3 v_normal;

// pomocnicza: oblicz wierzchołek + normalną per punkt (i,j)
void make_vertex(int i, int j, out vec4 pos, out float z, out float mask, out vec3 normal)
{
    vec2 texCoord = vec2(float(j) / float(u_width),
                         float(i) / float(u_height));
    vec2 rg = texture(u_gridTex, texCoord).rg;
    z = rg.r;
    mask = rg.g;

    float x = u_offsetX + j * u_stepX;
    float y = u_offsetY + i * u_stepY;
    pos = vec4(x, y, z, 1.0);

    // sąsiedzi do gradientu
    float z_left  = texture(u_gridTex, texCoord + vec2(-1.0/u_width, 0)).r;
    float z_right = texture(u_gridTex, texCoord + vec2( 1.0/u_width, 0)).r;
    float z_down  = texture(u_gridTex, texCoord + vec2(0, -1.0/u_height)).r;
    float z_up    = texture(u_gridTex, texCoord + vec2(0,  1.0/u_height)).r;

    float dzdx = (z_right - z_left) / (2.0 * u_stepX);
    float dzdy = (z_up - z_down) / (2.0 * u_stepY);

    normal = normalize(vec3(-dzdx, -dzdy, 1.0));
}

void main()
{
    int i = v_idx[0].x;
    int j = v_idx[0].y;

    vec4 v0, v1, v2, v3;
    float z0,z1,z2,z3;
    float m0,m1,m2,m3;
    vec3 n0,n1,n2,n3;

    make_vertex(i,   j,   v0, z0, m0, n0);
    make_vertex(i,   j+1, v1, z1, m1, n1);
    make_vertex(i+1, j,   v2, z2, m2, n2);
    make_vertex(i+1, j+1, v3, z3, m3, n3);

    if (m0 < 0.5 || m1 < 0.5 || m2 < 0.5 || m3 < 0.5)
        return;

    // quad jako triangle strip
    v_z=z0; v_mask=m0; v_normal=n0;
    gl_Position = u_mvp * v0; EmitVertex();

    v_z=z1; v_mask=m1; v_normal=n1;
    gl_Position = u_mvp * v1; EmitVertex();

    v_z=z2; v_mask=m2; v_normal=n2;
    gl_Position = u_mvp * v2; EmitVertex();

    v_z=z3; v_mask=m3; v_normal=n3;
    gl_Position = u_mvp * v3; EmitVertex();

    EndPrimitive();
}

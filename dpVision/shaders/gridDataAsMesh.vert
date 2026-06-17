#version 330 core
uniform int u_width;
uniform int u_height;

out ivec2 v_idx;

void main()
{
    int idx = gl_VertexID;          // numer kwadratu (0..(w-1)*(h-1)-1)
    int i = idx / (u_width - 1);
    int j = idx % (u_width - 1);

    v_idx = ivec2(i, j);
}

#version 330 core
// Fullscreen triangle – positions generated from gl_VertexID (no vertex buffer needed).
// gl_VertexID 0,1,2 → triangle that covers the entire NDC clip space.

out vec2 vTexCoord;

void main()
{
    vec2 pos    = vec2((gl_VertexID & 1) * 4.0 - 1.0,
                       (gl_VertexID >> 1) * 4.0 - 1.0);
    vTexCoord   = pos * 0.5 + 0.5;
    gl_Position = vec4(pos, 0.0, 1.0);
}

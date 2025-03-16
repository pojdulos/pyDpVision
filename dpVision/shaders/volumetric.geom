#version 330 core
layout(points) in;
layout(points, max_vertices = 1) out;

in VS_OUT{
	vec3 color;
	vec3 vPos;
	vec3 vScale;
	mat4 modelviewMatrix;
	mat4 projectionMatrix;
	bool isValid;
} gs_in[];

out vec3 vertexColor;

void main(void)
{
	if (gs_in[0].isValid)
	{
		vertexColor = gs_in[0].color;
		gl_Position = gs_in[0].projectionMatrix * gs_in[0].modelviewMatrix * vec4(gs_in[0].vPos, 1.0);

		EmitVertex();
		EndPrimitive();
	}
}

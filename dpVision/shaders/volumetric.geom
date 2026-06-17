#version 330 core
layout(points) in;
layout(points, max_vertices = 1) out;

in VS_OUT{
	vec3 color;
	vec3 vPos;
	vec3 vScale;
	mat4 modelviewMatrix;
	mat4 projectionMatrix;
	int isValid;
} gs_in[];

out vec3 vertexColor;
out vec3 FragPos;

void main(void)
{
	if (gs_in[0].isValid != 0)
	{
		vertexColor = gs_in[0].color;
		FragPos = gs_in[0].vPos;
		gl_Position = gs_in[0].projectionMatrix * gs_in[0].modelviewMatrix * vec4(gs_in[0].vPos, 1.0);

		EmitVertex();
		EndPrimitive();
	}
}

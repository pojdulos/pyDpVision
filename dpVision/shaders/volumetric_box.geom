#version 330 core
layout (points) in;
layout (triangle_strip, max_vertices = 36) out;

in VS_OUT {
    vec3 color;
	vec3 vPos;
	vec3 vScale;
	mat4 modelviewMatrix;
	mat4 projectionMatrix;
    int isValid;
} gs_in[];

out vec3 vertexColor;
out vec3 FragPos;

void main() {
    if (gs_in[0].isValid != 0) {
        vertexColor = gs_in[0].color;
        FragPos = gs_in[0].vPos;

        // Pozycja wierzchołka (punkt)
        vec4 pointPos = vec4(gs_in[0].vPos, 1.0);

        // Wierzchołki tworzące ściany kostki
        vec4 vertices[8];

        // Obliczenia pozycji wierzchołków
        vec3 halfSize = 0.5 * gs_in[0].vScale; // Połowa długości boku kostki
		
		// Wierzchołki kostki
        vertices[0] = pointPos + vec4(-halfSize[0], -halfSize[1], -halfSize[2], 0.0); // Lewy dolny tylny
		vertices[1] = pointPos + vec4( halfSize[0], -halfSize[1], -halfSize[2], 0.0); // Prawy dolny tylny
		vertices[2] = pointPos + vec4(-halfSize[0],  halfSize[1], -halfSize[2], 0.0); // Lewy górny tylny
		vertices[3] = pointPos + vec4( halfSize[0],  halfSize[1], -halfSize[2], 0.0); // Prawy górny tylny
		vertices[4] = pointPos + vec4(-halfSize[0], -halfSize[1],  halfSize[2], 0.0); // Lewy dolny przedni
		vertices[5] = pointPos + vec4( halfSize[0], -halfSize[1],  halfSize[2], 0.0); // Prawy dolny przedni
		vertices[6] = pointPos + vec4(-halfSize[0],  halfSize[1],  halfSize[2], 0.0); // Lewy górny przedni
		vertices[7] = pointPos + vec4( halfSize[0],  halfSize[1],  halfSize[2], 0.0); // Prawy górny przedni

		// TO TRZEBA ROZRYSOWAC I SPRAWDZIC !!!:
		int indices[20];
		indices[0] = 0;
		indices[1] = 1;
		indices[2] = 2;
		indices[3] = 3;
		indices[4] = 6;
		indices[5] = 7;
		indices[6] = 4;
		indices[7] = 5;
		indices[8] = 0;
		indices[9] = 1;

		indices[10] = 1;
		indices[11] = 5;
		indices[12] = 3;
		indices[13] = 7;
		indices[14] = 2;
		indices[15] = 6;
		indices[16] = 0;
		indices[17] = 4;
		indices[18] = 1;
		indices[19] = 5;

        // Generowanie ścian kostki
        for (int i = 0; i < 10; ++i) {
			int idx = indices[i];
            FragPos = vec3(vertices[idx]);
            gl_Position = gs_in[0].projectionMatrix * gs_in[0].modelviewMatrix * vertices[idx];
            EmitVertex();
        }
        EndPrimitive();
        for (int i = 10; i < 20; ++i) {
			int idx = indices[i];
            FragPos = vec3(vertices[idx]);
            gl_Position = gs_in[0].projectionMatrix * gs_in[0].modelviewMatrix * vertices[idx];
            EmitVertex();
        }
        EndPrimitive();
    }
}

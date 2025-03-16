#version 330 core
in vec3 smoothVertexNormal;
flat in vec3 flatVertexNormal;
in vec4 vertexColor;
in vec2 TexCoord;  // Współrzędne tekstury dodane do wejść
in vec3 FragPos; // Pozycja fragmentu/prymitywu w przestrzeni świata

uniform sampler2D texture1;  // Sampler tekstury
uniform bool useTexture;
uniform bool useFlatShading;

out vec4 FragColor;

void main()
{
    vec3 lightPos = vec3(0, 100, 600);  // Pozycja światła
    vec3 viewPos = vec3(0, 0, 200);  // Pozycja obserwatora/kamery
    vec3 lightColor = vec3(1.0, 1.0, 1.0);  // Kolor światła
    float ambientStrength = 0.6;
    float specularStrength = 0.5;  // Siła światła spekularnego
    float shininess = 32.0;  // Połysk (shininess)

    // Obliczenia oświetlenia (tutaj możesz dodać własną logikę)
   	vec3 norm = normalize( useFlatShading ? flatVertexNormal : smoothVertexNormal );
    
    vec3 lightDir = normalize(lightPos - FragPos);  // Poprawione obliczanie kierunku światła
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;

    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), shininess);
    vec3 specular = specularStrength * spec * lightColor;

    vec3 result = (ambientStrength * lightColor + diffuse + specular) * vertexColor.rgb;

    if (useTexture)
    {
		vec4 texColor = texture(texture1, TexCoord);  // Odczytanie koloru z tekstury
		FragColor = vec4(result, 1.0) * texColor;  // Mieszanie koloru tekstury z oświetleniem
	  }
    else
    {
		FragColor = vec4(result, vertexColor.a);
	}
}

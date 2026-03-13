#version 330 core

uniform vec3 u_tint;

in vec3  v_color;
in float v_valid;

out vec4 fragColor;

void main()
{
	if (v_valid < 0.5)
		discard;

	// Gaussowski profil intensywności na podstawie gl_PointCoord
	vec2  uv = gl_PointCoord * 2.0 - 1.0;
	float r2 = dot(uv, uv);
	float alpha = exp(-r2 * 2.0);

	if (alpha < 0.01)
		discard;

	fragColor = vec4(v_color * u_tint, alpha);
}

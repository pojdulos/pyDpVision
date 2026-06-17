#version 330 core

uniform vec3 u_tint;
uniform bool u_depth_prepass;
uniform float u_depth_cutoff;

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
	float alpha = exp(-r2 * 1.5);

	float cutoff = u_depth_prepass ? u_depth_cutoff : 0.01;
	if (alpha < cutoff)
		discard;

	if (u_depth_prepass) {
		fragColor = vec4(0.0);
		return;
	}

	fragColor = vec4(v_color * u_tint, alpha);
}

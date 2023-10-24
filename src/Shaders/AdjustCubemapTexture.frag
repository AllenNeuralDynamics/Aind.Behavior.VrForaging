#version 400

uniform float brightness = 0.0;
uniform float contrast = 1.0;

uniform samplerCube tex;

in vec4 texCoord;
out vec4 fragColor;

mat4 brightnessMatrix(float brightness)
{
    return mat4( 1, 0, 0, 0,
                 0, 1, 0, 0,
                 0, 0, 1, 0,
                 brightness, brightness, brightness, 1 );
}

mat4 contrastMatrix(float contrast)
{
	float t = ( 1.0 - contrast ) / 2.0;
    return mat4( contrast, 0, 0, 0,
                 0, contrast, 0, 0,
                 0, 0, contrast, 0,
                 t, t, t, 1 );
}

void main()
{
  vec4 texel = texture(tex, texCoord.xyz);
	fragColor = brightnessMatrix(brightness) *
        		contrastMatrix(contrast) *
        		texel;
}
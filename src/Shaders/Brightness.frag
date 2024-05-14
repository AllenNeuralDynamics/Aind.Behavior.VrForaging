#version 400

uniform sampler2D tex;
uniform brightness = 1.0;
in vec2 texCoord;

out vec4 fragColor;

void main()
{
  vec4 texel = texture(tex, texCoord);
  texel.rgb *= brightness;
  fragColor = texel;
}
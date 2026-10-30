#version 330

in vec2 a_pos;
in vec2 a_uv;

out vec2 v_uv;

void main() {
    gl_Position = vec4(a_pos.x, -a_pos.y, 0.0, 1.0);
    v_uv = a_uv;
}

#version 330

uniform sampler2D u_texture;
uniform float u_time;
uniform float u_speed;
uniform float u_distortion;
uniform float u_noise_scale;
uniform float u_swirl;
uniform float u_swirl_scale;
uniform float u_vignette;
uniform vec2 u_resolution;
uniform vec2 u_tex_size;

in vec2 v_uv;
layout(location = 0) out vec4 fragColor;

float hash(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float value_noise(vec2 p) {
    vec2 cell = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    float a = hash(cell);
    float b = hash(cell + vec2(1.0, 0.0));
    float c = hash(cell + vec2(0.0, 1.0));
    float d = hash(cell + vec2(1.0, 1.0));
    return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p) {
    float value = 0.0;
    float weight = 0.5;
    for (int octave = 0; octave < 3; octave++) {
        value += weight * value_noise(p);
        p = p * 2.03 + vec2(1.7, 9.2);
        weight *= 0.5;
    }
    return value;
}

vec2 mirror_uv(vec2 uv) {
    vec2 wrapped = mod(uv, 2.0);
    vec2 flipped = step(1.0, wrapped);
    return mix(wrapped, 2.0 - wrapped, flipped);
}

vec2 cover_uv(vec2 uv) {
    float screen_aspect = u_resolution.x / max(u_resolution.y, 1.0);
    float texture_aspect = u_tex_size.x / max(u_tex_size.y, 1.0);
    vec2 fitted = vec2(1.0);
    if (screen_aspect > texture_aspect) {
        fitted.y = texture_aspect / screen_aspect;
    } else {
        fitted.x = screen_aspect / texture_aspect;
    }
    return (uv - 0.5) * fitted + 0.5;
}

vec2 curl_flow(vec2 uv, float t) {
    vec2 sum = vec2(0.0);
    for (int index = 0; index < 3; index++) {
        float id = float(index);
        vec2 center = vec2(
            0.5 + 0.30 * sin(t * 0.07 + id * 2.094395),
            0.5 + 0.30 * cos(t * 0.05 + id * 2.094395)
        );
        vec2 radial = uv - center;
        float distance = length(radial);
        float weight = exp(-distance * distance * (1.6 + u_swirl_scale * 0.45));
        vec2 tangent = distance > 0.0001 ? vec2(-radial.y, radial.x) / distance : vec2(0.0);
        float spin = sin(t * 0.16 + id * 1.7 + u_swirl_scale * radial.x);
        sum += tangent * weight * spin;
    }
    return sum * u_swirl;
}

void main() {
    vec2 uv = cover_uv(v_uv);
    float t = u_time * u_speed;
    vec2 domain = uv * u_noise_scale;
    vec2 q = vec2(
        fbm(domain + vec2(0.0, t * 0.17)),
        fbm(domain + vec2(5.2, 1.3) - vec2(t * 0.13, t * 0.09))
    );
    vec2 r = vec2(
        fbm(domain + q * 1.75 + vec2(1.7, 9.2) + vec2(t * 0.08, -t * 0.05)),
        fbm(domain + q * 1.75 + vec2(8.3, 2.8) - vec2(t * 0.06, t * 0.07))
    );
    vec2 sine = vec2(
        sin(uv.y * 6.0 + t + r.x * 4.0) * 0.62 + sin(uv.y * 2.15 - t * 0.73 + q.y * 3.0) * 0.38,
        cos(uv.x * 5.0 - t * 0.81 + r.y * 4.0) * 0.62 + cos(uv.x * 2.65 + t * 0.57 + q.x * 3.0) * 0.38
    );
    vec2 offset = sine * u_distortion;
    offset += (r - 0.5) * (u_distortion * 1.35);
    offset += curl_flow(uv, t);
    vec3 color = texture(u_texture, mirror_uv(uv + offset)).rgb;
    vec2 from_center = v_uv * 2.0 - 1.0;
    float shade = smoothstep(0.28, 1.2, dot(from_center, from_center));
    color = mix(color, color * vec3(0.40, 0.26, 0.16), shade * u_vignette);
    fragColor = vec4(color, 1.0);
}

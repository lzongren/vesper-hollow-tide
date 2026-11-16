"""Scalp-fitted down and loose tendrils at the front of the ear, in rest metres."""

from math import atan2, cos, hypot, pi, sin, sqrt


def dress_temples(patch, material, combed, edge_row, scalp, smooth):
    head = [("head", 1)]
    axis_z = 0.02496

    for side in (-1, 1):
        # Short hairs emerge from inside the dense combed margin and lie
        # flush along the forehead. Break up both the edge and the endpoints.
        for tuft in range(23):
            phase = tuft * 2.399 + side
            root = 0.20 + tuft * 0.044 + 0.014 * sin(phase)
            length = 0.051 + 0.016 * cos(phase) + 0.015 * root

            def down(u, v):
                a = side * (root + 0.040 * v + (u - 0.5) * (0.092 - 0.034 * v))
                row = edge_row(a) + 0.019 - length * v
                x, y, z = combed(a, row)
                lift = 0.00045 + 0.00022 * sin(pi * v)
                return (
                    (x + lift * sin(a), y, z + lift * cos(a)),
                    ((tuft % 4 + u) / 4, v),
                    head,
                )

            patch(material, 5, 14, down)

        # Root azimuth, sweep, drop in metres, root width, body bow and tip return.
        # One long family turns back beneath the lobe. The neighboring families
        # break away at the ear notch, the lobe and the upper neck respectively.
        guides = (
            (0.62, 0.23, 0.039, 0.124, 0.0, 0.0),
            (0.78, 0.20, 0.052, 0.142, 0.0, 0.0),
            (0.95, 0.17, 0.039, 0.145, 0.0, 0.0),
            (1.034, 0.196, 0.111, 0.142, -0.025, -0.040),
            (1.174, 0.084, 0.156, 0.148, 0.034, -0.035),
            (1.23, 0.04, 0.048, 0.114, 0.0, 0.0),
            (1.086, 0.143, 0.097, 0.158, -0.009, 0.074),
            (0.978, 0.222, 0.067, 0.131, 0.024, -0.022),
            (1.110, 0.098, 0.138, 0.121, 0.018, 0.036),
        )
        for i, (root, arc, drop, width, bend, tip_return) in enumerate(guides):
            phase = 2.399 * i + 0.48 * side
            atlas_strip = 2 if i == 8 else i % 4
            # These three guides cross the same exposed patch above the ear.
            # In that patch sample the thinner portion of their own fibers.
            shaft_advance = {3: 0.15, 6: 0.13, 8: 0.20}.get(i, 0.0)
            # The two companion wisps part below the lobe, one toward the
            # neck and the shorter one toward the jaw. Their tips ease back.
            curl_start, curl_angle = {4: (0.62, 0.035), 6: (0.73, -0.031)}.get(
                i, (0.62, 0.0)
            )

            def tendril(u, v):
                across = (u - 0.5) * width
                a = side * (root + 0.013 * sin(phase) + across)
                x, y, z = combed(a, edge_row(a) + 0.020 + 0.009 * sin(phase))
                root_angle = atan2(x, z - axis_z)
                root_radius = hypot(x, z - axis_z)
                # The guide leaves the swept roots tangentially, then turns
                # downwards. Thin the geometry without pinching all tips together.
                # The ends fan in opposite directions after clearing the pinna,
                # while their roots still follow the original swept hairline.
                loose = smooth((drop - 0.060) / 0.060)
                turn = smooth((v - 0.38) / 0.62)
                curl_t = max(0.0, (v - curl_start) / (1 - curl_start))
                lower_curl = curl_angle * sin(pi * curl_t) ** 2
                angle = root_angle + side * (
                    arc * sin(0.60 * pi * v)
                    + 0.038 * sin(1.75 * pi * v) * sin(phase)
                    + bend * sin(pi * v)
                    + 0.050 * smooth((drop - 0.060) / 0.040) * v * sin(1.50 * pi * v)
                    + tip_return * turn
                    + lower_curl
                    + 0.38 * across * loose * turn * sin(phase)
                    - 0.52 * across * v
                )
                side_length = 1 + 0.055 * loose * (2 * u - 1) * sin(phase)
                y -= (
                    drop
                    * side_length
                    * (0.96 + 0.04 * cos(phase))
                    * (0.80 * v + 0.20 * v * v)
                )
                h = 7 + (y - 1.625) / 0.103
                section = 0.104 * scalp(angle, h, root_radius / 0.104)
                # Loose ends can hang away from the receding jaw. Use a
                # smooth maximum so no crease forms where the cheek recedes.
                free = root_radius - (0.0045 + 0.0015 * cos(phase)) * v
                radius = 0.5 * (
                    section + free + sqrt((section - free) ** 2 + 0.0015**2)
                )
                weight = smooth(v / 0.22)
                radius = root_radius + weight * (
                    radius + 0.0009 + 0.0016 * sin(pi * v) - root_radius
                )
                fiber_u = 1 - u if i == 8 else u
                fiber_v = v - 0.045 * loose * sin(pi * v)
                shaft = smooth((v - 0.035) / 0.165) * (1 - smooth((v - 0.28) / 0.40))
                fiber_v += shaft_advance * shaft
                return (
                    (radius * sin(angle), y, axis_z + radius * cos(angle)),
                    ((atlas_strip + fiber_u) / 4, fiber_v),
                    head,
                )

            patch(material, 7, 36, tendril)

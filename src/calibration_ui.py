import cv2


def draw_calibration_overlay(frame, progress=0.0, score=0.0, reason=""):
    output = frame.copy()
    h, w = output.shape[:2]

    cx = w // 2
    shoulder = int(min(w, h) * 0.16)
    arm = int(min(w, h) * 0.18)

    sy = int(h * 0.43)
    hy = int(h * 0.67)
    head_y = int(h * 0.29)

    ls = (cx - shoulder, sy)
    rs = (cx + shoulder, sy)
    le = (cx - shoulder - arm, sy)
    re = (cx + shoulder + arm, sy)
    lw = (cx - shoulder - arm * 2, sy)
    rw = (cx + shoulder + arm * 2, sy)

    if progress >= 1.0:
        color = (0, 255, 0)
    elif score >= 0.70:
        color = (0, 220, 255)
    else:
        color = (255, 180, 0)

    thickness = max(3, int(min(w, h) / 300))

    cv2.circle(output, (cx, head_y), max(18, int(min(w, h) * 0.055)), color, thickness)
    cv2.line(output, ls, (cx, hy), color, thickness)
    cv2.line(output, rs, (cx, hy), color, thickness)
    cv2.line(output, ls, le, color, thickness)
    cv2.line(output, le, lw, color, thickness)
    cv2.line(output, rs, re, color, thickness)
    cv2.line(output, re, rw, color, thickness)

    for point in (ls, rs, le, re, lw, rw):
        cv2.circle(output, point, max(6, thickness * 2), color, -1)

    # Caja grande para que la referencia se vea realmente en calibracion.
    margin_x = int(w * 0.10)
    margin_y = int(h * 0.08)
    cv2.rectangle(
        output,
        (margin_x, margin_y),
        (w - margin_x, h - margin_y),
        color,
        2,
    )

    cv2.rectangle(
        output,
        (0, 0),
        (w, 110),
        (15, 15, 15),
        -1,
    )

    percent = int(progress * 100)

    cv2.putText(
        output,
        "CALIBRACION - TORSE + BRAZOS",
        (25, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        color,
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        output,
        f"Estabilidad: {percent}%   Score: {score:.2f}",
        (25, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        color,
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        output,
        reason[:80],
        (25, 98),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.52,
        color,
        2,
        cv2.LINE_AA,
    )

    return output


# Compatibilidad con codigo anterior.
draw_t_pose_guide = draw_calibration_overlay

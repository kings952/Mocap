import cv2


def draw_t_pose_guide(
    frame,
    progress=0.0,
    score=0.0,
):
    """
    Guía visual pequeña para T-pose.

    No ocupa toda la pantalla porque la cámara puede
    no tener espacio para mostrar el cuerpo completo.
    """

    output = frame.copy()

    height, width = output.shape[:2]

    # --------------------------------------------------------
    # Centro
    # --------------------------------------------------------

    cx = width // 2

    # Tamaño relativo de la guía.
    shoulder = int(width * 0.10)

    arm = int(width * 0.13)

    head_radius = int(width * 0.025)

    # Posición aproximada del torso superior.
    shoulder_y = int(
        height * 0.42
    )

    head_y = int(
        height * 0.31
    )

    hip_y = int(
        height * 0.63
    )

    left_shoulder = (
        cx - shoulder,
        shoulder_y,
    )

    right_shoulder = (
        cx + shoulder,
        shoulder_y,
    )

    left_elbow = (
        cx - shoulder - arm,
        shoulder_y,
    )

    right_elbow = (
        cx + shoulder + arm,
        shoulder_y,
    )

    left_hand = (
        cx - shoulder - arm * 2,
        shoulder_y,
    )

    right_hand = (
        cx + shoulder + arm * 2,
        shoulder_y,
    )

    # --------------------------------------------------------
    # Color
    # --------------------------------------------------------

    if progress >= 1.0:
        color = (0, 255, 0)
    elif score >= 0.65:
        color = (0, 220, 255)
    else:
        color = (255, 180, 0)

    thickness = 3

    # --------------------------------------------------------
    # Cabeza
    # --------------------------------------------------------

    cv2.circle(
        output,
        (cx, head_y),
        head_radius,
        color,
        thickness,
    )

    # --------------------------------------------------------
    # Torso
    # --------------------------------------------------------

    cv2.line(
        output,
        left_shoulder,
        (cx, hip_y),
        color,
        thickness,
    )

    cv2.line(
        output,
        right_shoulder,
        (cx, hip_y),
        color,
        thickness,
    )

    # --------------------------------------------------------
    # Brazos
    # --------------------------------------------------------

    cv2.line(
        output,
        left_shoulder,
        left_elbow,
        color,
        thickness,
    )

    cv2.line(
        output,
        left_elbow,
        left_hand,
        color,
        thickness,
    )

    cv2.line(
        output,
        right_shoulder,
        right_elbow,
        color,
        thickness,
    )

    cv2.line(
        output,
        right_elbow,
        right_hand,
        color,
        thickness,
    )

    # --------------------------------------------------------
    # Puntos
    # --------------------------------------------------------

    points = [
        left_shoulder,
        right_shoulder,
        left_elbow,
        right_elbow,
        left_hand,
        right_hand,
    ]

    for point in points:
        cv2.circle(
            output,
            point,
            6,
            color,
            -1,
        )

    # --------------------------------------------------------
    # Texto
    # --------------------------------------------------------

    cv2.putText(
        output,
        "CALIBRACION - T POSE",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
        cv2.LINE_AA,
    )

    percent = int(
        progress * 100
    )

    cv2.putText(
        output,
        f"Estabilidad: {percent}%",
        (20, 70),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        color,
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        output,
        "Mantente quieto con los brazos abiertos",
        (20, height - 25),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        color,
        2,
        cv2.LINE_AA,
    )

    return output
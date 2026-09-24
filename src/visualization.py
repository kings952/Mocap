import cv2


def draw_status(
    frame,
    state,
    frame_id=0,
    calibration_progress=0.0,
):
    output = frame.copy()

    height, width = output.shape[:2]

    # --------------------------------------------------------
    # Fondo de información
    # --------------------------------------------------------

    cv2.rectangle(
        output,
        (0, 0),
        (width, 90),
        (0, 0, 0),
        -1,
    )

    # --------------------------------------------------------
    # Estado
    # --------------------------------------------------------

    cv2.putText(
        output,
        f"ESTADO: {state}",
        (15, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        output,
        f"FRAME: {frame_id}",
        (15, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    if state == "CALIBRATING":

        percent = int(
            calibration_progress * 100
        )

        cv2.putText(
            output,
            f"CALIBRACION: {percent}%",
            (220, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 220, 255),
            2,
            cv2.LINE_AA,
        )

    if state == "RECORDING":

        cv2.putText(
            output,
            "Q = SALIR",
            (width - 130, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    return output
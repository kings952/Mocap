import subprocess
from pathlib import Path

from config import (
    BLENDER_EXE,
    SOURCE_BLEND,
    BLENDER_GENERATOR,
)


class BlenderController:

    def __init__(self):

        if not BLENDER_EXE.exists():

            raise FileNotFoundError(
                f"Blender no encontrado: "
                f"{BLENDER_EXE}"
            )

        if not SOURCE_BLEND.exists():

            raise FileNotFoundError(
                f".blend original no encontrado: "
                f"{SOURCE_BLEND}"
            )

    def generate(
        self,
        poses_file,
        output_file,
    ):

        poses_file = Path(
            poses_file
        ).resolve()

        output_file = Path(
            output_file
        ).resolve()

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command = [

            str(BLENDER_EXE),

            "-b",

            str(SOURCE_BLEND),

            "--python",

            str(
                BLENDER_GENERATOR
            ),

            "--",

            "--poses",

            str(poses_file),

            "--output",

            str(output_file),
        ]

        print(
            "\n[BLENDER]"
            "\nGenerando archivo..."
        )

        result = subprocess.run(
            command,
            cwd=str(
                BLENDER_EXE.parent
            ),
            text=True,
        )

        if result.returncode != 0:

            raise RuntimeError(
                "Blender terminó con "
                f"código {result.returncode}"
            )

        return output_file
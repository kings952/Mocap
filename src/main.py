import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from PySide6.QtWidgets import QApplication

from src.app import (
    MocapApplication,
)


def main():

    app = QApplication(
        sys.argv
    )

    controller = (
        MocapApplication()
    )

    result = app.exec()

    controller.close()

    sys.exit(result)


if __name__ == "__main__":
    main()